"""Adapt the attributed M24 source animation to the installed V9 bare arms.

Blender background authoring only. Retains the V9 bind, UVs, weights and
corrective shapes. The native/source import is a separate, untouched asset.
"""
import bpy, json, math, ast
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

O = Path(__file__).resolve().parent
X = O / 'GameplayExports'
(X / 'Animations').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O / 'M24_CustomScope_Native_Editable.blend'), use_scripts=False)
s = bpy.context.scene
I = Matrix.Identity(4)
C = Matrix.Rotation(math.pi, 4, 'Z')
native = bpy.data.objects['M24_SourceRig']
sr = {b.name: C @ b.matrix_local for b in native.data.bones}
source = []
for f in range(1, 202):
    s.frame_set(f)
    source.append({b.name: C @ b.matrix for b in native.pose.bones})
s.frame_set(1)
parts = [o for o in s.objects if o.type == 'MESH' and o.name != 'M24_SourceNativeArms']
for ob in parts:
    ob.parent = None
    ob.matrix_world = I
    ob.modifiers.clear()
    ob.data.transform(C)
bpy.data.objects.remove(bpy.data.objects['M24_SourceNativeArms'], do_unlink=True)
bpy.data.objects.remove(native, do_unlink=True)
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(O / 'V9/M4_V9_Template.fbx'), use_anim=False)
imported = [o for o in bpy.data.objects if o not in before]
r = next(o for o in imported if o.type == 'ARMATURE')
r.name = 'M24_V9_Rig'
template = next(o for o in imported if o.type == 'MESH')

# Extract the two existing skin sections, including every original morph.
# Reindex all shape and UV data together; never deform the accepted rest skin.
skin_slots = {i for i,m in enumerate(template.data.materials) if m and 'SkinV9' in m.name}
faces = [p for p in template.data.polygons if p.material_index in skin_slots]
used = sorted({v for p in faces for v in p.vertices})
remap = {v:i for i,v in enumerate(used)}
me = bpy.data.meshes.new('M24_V9_BareArms')
me.from_pydata([template.data.vertices[v].co[:] for v in used], [],
              [[remap[v] for v in p.vertices] for p in faces])
skin = bpy.data.objects.new('M24_V9_BareArms', me)
s.collection.objects.link(skin)
skin.matrix_world = template.matrix_world.copy()
for i in sorted(skin_slots):
    me.materials.append(template.data.materials[i])
slotmap = {v:i for i,v in enumerate(sorted(skin_slots))}
for dst,src in zip(me.polygons, faces):
    dst.material_index = slotmap[src.material_index]
    dst.use_smooth = src.use_smooth
loops = [i for p in faces for i in p.loop_indices]
for uv in template.data.uv_layers:
    layer = me.uv_layers.new(name=uv.name)
    values = np.empty(len(uv.data)*2, dtype=np.float32)
    uv.data.foreach_get('uv', values)
    layer.data.foreach_set('uv', values.reshape(-1,2)[loops].ravel())
for vg in template.vertex_groups:
    skin.vertex_groups.new(name=vg.name)
for old,new in remap.items():
    for g in template.data.vertices[old].groups:
        skin.vertex_groups[g.group].add([new], g.weight, 'REPLACE')
if template.data.shape_keys:
    for block in template.data.shape_keys.key_blocks:
        key = skin.shape_key_add(name=block.name, from_mix=False)
        values = np.empty(len(block.data)*3, dtype=np.float32)
        block.data.foreach_get('co', values)
        key.data.foreach_set('co', values.reshape(-1,3)[used].ravel())
        key.value = 0
        key.slider_min, key.slider_max = block.slider_min, block.slider_max
# Preserve the exact V9 rest coordinates; the exported rig transform is rigid.
skin.data.transform(r.matrix_world.inverted() @ skin.matrix_world)
skin.matrix_world = I
r.matrix_world = I
bpy.data.objects.remove(template, do_unlink=True)
for ob in imported:
    if ob not in (r, template) and ob.name in bpy.data.objects:
        bpy.data.objects.remove(ob, do_unlink=True)

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:
        ob.hide_set(False); ob.select_set(True)
    bpy.context.view_layer.objects.active = r

select([r])
bpy.ops.object.mode_set(mode='EDIT')
eb = r.data.edit_bones
for b in list(eb):
    if b.name.startswith('WPN_'):
        eb.remove(b)
gun_rest = Matrix.Translation(sr['WPN_root'].translation)
for n,m in sr.items():
    if not n.startswith('WPN_'): continue
    b = eb.new(n)
    b.matrix = gun_rest if n == 'WPN_root' else m
    b.length = .025
    b.parent = eb['VM_Root'] if n == 'WPN_root' else eb['WPN_root']
eb['WPN_BoltHandle'].parent = eb['WPN_BoltCarrier']
eb['WPN_Cartridge'].parent = eb['WPN_Magazine']

def bounds(name):
    v = np.array([p.co[:] for p in bpy.data.objects[name].data.vertices])
    return v.min(axis=0), v.max(axis=0)
lo,hi = bounds('M24_ScopeGlass_Lowpoly')
rear = Vector(((lo[0]+hi[0])/2, lo[1], (lo[2]+hi[2])/2))
front = rear.copy(); front.y = hi[1]
lo,hi = bounds('M24_silencer')
muzzle = Vector(((lo[0]+hi[0])/2, hi[1], (lo[2]+hi[2])/2))
markers = {'WPN_RearSight':rear, 'WPN_FrontSight':front,
           'WPN_SOCKET_Muzzle':muzzle, 'WPN_Eject':sr['WPN_BoltCarrier'].translation,
           'WPN_SOCKET_Magazine':sr['WPN_Magazine'].translation}
body_points=np.array([v.co[:] for v in bpy.data.objects['M24_base'].data.vertices])
butt=body_points[body_points[:,1]<body_points[:,1].min()+.025].mean(axis=0)
markers['WPN_StockContact']=Vector(butt)
for n,p in markers.items():
    b = eb.new(n); b.matrix = Matrix.Translation(p); b.length = .02; b.parent = eb['WPN_root']
bpy.ops.object.mode_set(mode='OBJECT')
for ob in [skin,*parts]:
    ob.parent = r; ob.matrix_parent_inverse = I; ob.matrix_basis = I
    ob.modifiers.new('M24 V9 Skin', 'ARMATURE').object = r
for m in skin.data.materials: m.name = 'MI_Manny_01' if m == skin.data.materials[0] else 'MI_Manny_02'
rest = {b.name:b.matrix_local.copy() for b in r.data.bones}
parents = {b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest = {n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}

def frame(direction, transverse):
    y = direction.normalized()
    x = (transverse-y*transverse.dot(y)).normalized()
    z = x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_4x4()

def under(n, ancestor):
    while n:
        if n == ancestor: return True
        n = parents.get(n)
    return False

corrections = {}; fmap = {}; offsets = {}
for side in ('l','r'):
    a = side.upper()+'_'
    hn = 'hand_'+side
    sf = frame(sr[a+'middle1'].translation-sr[a+'wrist'].translation,
               sr[a+'point1'].translation-sr[a+'pink1'].translation)
    tf = frame(rest['middle_01_'+side].translation-rest[hn].translation,
               rest['index_01_'+side].translation-rest['pinky_01_'+side].translation)
    rq = (sf@tf.inverted()).to_quaternion()
    corrections[hn] = sr[a+'wrist'].to_quaternion().inverted() @ rq @ rest[hn].to_quaternion()
    # Register the middle knuckle, so a different wrist-to-palm length does
    # not move the support contact away from the same original rifle.
    target_delta = rq @ (rest['middle_01_'+side].translation-rest[hn].translation)
    offsets[side] = sr[a+'wrist'].to_quaternion().inverted() @ (
        sr[a+'middle1'].translation - target_delta - sr[a+'wrist'].translation)
    for donor,target,nextdonor,nexttarget in (
        ('arm','upperarm','elbow','lowerarm'),('elbow','lowerarm','wrist','hand')):
        sd = sr[a+nextdonor].translation-sr[a+donor].translation
        td = rest[nexttarget+'_'+side].translation-rest[target+'_'+side].translation
        wanted = frame(sd, sf.col[0].to_3d()) @ frame(td, tf.col[0].to_3d()).inverted()
        corrections[target+'_'+side] = sr[a+donor].to_quaternion().inverted() @ wanted.to_quaternion() @ rest[target+'_'+side].to_quaternion()
    for dn,tn in [('thumb','thumb'),('point','index'),('middle','middle'),('ring','ring'),('pink','pinky')]:
        for j in (1,2,3):
            donor = a+dn+str(j); target = f'{tn}_{j:02d}_{side}'
            snext = a+dn+str(j+1) if j<3 else None
            tnext = f'{tn}_{j+1:02d}_{side}' if j<3 else None
            sd = sr[snext].translation-sr[donor].translation if snext else sr[donor].to_3x3()@Vector((0,1,0))
            td = rest[tnext].translation-rest[target].translation if tnext else rest[target].to_3x3()@Vector((0,1,0))
            fq = (frame(sd,sf.col[0].to_3d())@frame(td,tf.col[0].to_3d()).inverted()).to_quaternion()
            corrections[target] = sr[donor].to_quaternion().inverted() @ fq @ rest[target].to_quaternion()
            fmap[target] = donor

def solve_arm(row, side, hand, pose):
    a = side.upper()+'_'; un='upperarm_'+side; ln='lowerarm_'+side; hn='hand_'+side; cn='clavicle_'+side
    shoulder = pose[a+'arm'].translation.copy()
    elbow = rest[ln].translation; wrist=rest[hn].translation
    l1=(elbow-rest[un].translation).length; l2=(wrist-elbow).length
    goal=hand.translation; axis=goal-shoulder; distance=axis.length
    reach=.97*(l1+l2)
    if distance>reach: shoulder+=axis.normalized()*(distance-reach)
    axis=goal-shoulder; distance=max(axis.length,abs(l1-l2)+1e-5); axis.normalize()
    pole=pose[a+'elbow'].translation-shoulder; pole-=axis*pole.dot(axis)
    if pole.length<1e-7: pole=Vector((0,0,-1)).cross(axis)
    pole.normalize(); along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    ep=shoulder+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    uq=pose[a+'arm'].to_quaternion()@corrections[un]
    lq=pose[a+'elbow'].to_quaternion()@corrections[ln]
    ua=rest[un].to_quaternion().inverted()@(elbow-rest[un].translation)
    la=rest[ln].to_quaternion().inverted()@(wrist-elbow)
    uq=(uq@ua).rotation_difference(ep-shoulder)@uq
    lq=(lq@la).rotation_difference(goal-ep)@lq
    um=Matrix.LocRotScale(shoulder,uq,Vector((1,1,1)))
    lm=Matrix.LocRotScale(ep,lq,Vector((1,1,1)))
    row[cn]=rest[cn].copy(); row[cn].translation+=shoulder-rest[un].translation
    for n in row:
        if under(n,hn): row[n]=hand@rest[hn].inverted()@rest[n]
        elif under(n,ln): row[n]=lm@rest[ln].inverted()@rest[n]
        elif under(n,un): row[n]=um@rest[un].inverted()@rest[n]

def retarget(pose):
    row={n:m.copy() for n,m in rest.items()}
    motion=pose['WPN_root']@sr['WPN_root'].inverted()
    for n in row:
        if n.startswith('WPN_'):
            row[n]=pose[n]@sr[n].inverted()@rest[n] if n in sr else motion@rest[n]
    for side in ('l','r'):
        donor=side.upper()+'_wrist'; hn='hand_'+side
        q=pose[donor].to_quaternion()@corrections[hn]
        hand=Matrix.LocRotScale(pose[donor].translation+pose[donor].to_quaternion()@offsets[side],q,Vector((1,1,1)))
        solve_arm(row,side,hand,pose)
        for target,donor in fmap.items():
            if not target.endswith('_'+side):continue
            p=parents[target]; pos=row[p]@local_rest[target].translation
            row[target]=Matrix.LocRotScale(pos,pose[donor].to_quaternion()@corrections[target],Vector((1,1,1)))
    return row

def mix(a,b,w):
    p,q,sc=a.decompose(); p2,q2,sc2=b.decompose()
    return Matrix.LocRotScale(p.lerp(p2,w),q.slerp(q2,w),sc.lerp(sc2,w))
def blend(a,b,w):return {n:mix(a[n],b[n],w) for n in a}
def ease(t):t=max(0.,min(1.,t));return t*t*(3-2*t)
native_rows=[retarget(p) for p in source]
idle=native_rows[0]

def settled(start,end,lead=0,tail=6):
    rows=[{n:m.copy() for n,m in row.items()} for row in native_rows[start-1:end]]
    if lead:
        rows=[blend(idle,rows[0],ease(i/lead)) for i in range(lead)]+rows
    if tail:
        rows += [blend(rows[-1],idle,ease((i+1)/tail)) for i in range(tail)]
    return rows

clips={'idle':[idle,idle], 'fire':settled(1,50,tail=6),
       'reload':settled(50,98,lead=6,tail=6), 'cycle':settled(98,148,lead=6,tail=6)}
clips['reload_empty']=settled(50,148,lead=6,tail=6)
# Draw and inspection are newly authored on this grip, explicitly distinct
# from the unnamed source timeline segments. Locomotion remains procedural.
def held_motion(d):
    row={n:m.copy() for n,m in idle.items()}
    pose={n:d@m for n,m in source[0].items()}
    for n in row:
        if n.startswith('WPN_'):row[n]=d@idle[n]
    for side in ('l','r'):
        solve_arm(row,side,d@idle['hand_'+side],pose)
        # The arm solver uses the native bind for descendants. Restore the
        # closed M24 finger pose for rigid held-weapon gestures.
        for n in row:
            if under(n,'hand_'+side):row[n]=d@idle[n]
    return row
equip=[]
for f in range(25):
    w=1-ease(f/24)
    d=Matrix.Translation((.06*w,-.12*w,-.24*w))@Matrix.Translation(idle['hand_r'].translation)@Matrix.Rotation(-.32*w,4,'X')@Matrix.Translation(-idle['hand_r'].translation)
    equip.append(held_motion(d))
clips['equip']=equip
inspect=[]
for f in range(91):
    t=f/90; w=math.sin(math.pi*t)**2
    angle=.42*w*math.sin(2*math.pi*t)
    d=Matrix.Translation((0,-.035*w,.035*w))@Matrix.Translation(idle['hand_r'].translation)@Matrix.Rotation(angle,4,'Y')@Matrix.Translation(-idle['hand_r'].translation)
    inspect.append(held_motion(d))
clips['inspect']=inspect
melee=[]
for f in range(28):
    t=f/27
    knots=[(0.,0.),(3/27,-.12),(5/27,1.),(8/27,.78),(1.,0.)]
    a,b=next((a,b) for a,b in zip(knots,knots[1:]) if a[0]<=t<=b[0])
    w=a[1]+(b[1]-a[1])*ease((t-a[0])/(b[0]-a[0]))
    pivot=idle['hand_r'].translation
    d=Matrix.Translation((-.10*w,.16*w,.025*w))@Matrix.Translation(pivot)@Matrix.Rotation(-1.3*w,4,'Z')@Matrix.Rotation(.32*w,4,'X')@Matrix.Translation(-pivot)
    melee.append(held_motion(d))
clips['quick_melee']=melee

def twists(rows):
    for side in ('l','r'):
        ln='lowerarm_'+side; hn='hand_'+side
        axis=rest[ln].to_quaternion().inverted()@(rest[hn].translation-rest[ln].translation).normalized()
        ref=rest[ln].to_quaternion().inverted()@rest[hn].to_quaternion()
        values=[]
        for row in rows:
            q=(row[ln].to_quaternion().inverted()@row[hn].to_quaternion())@ref.inverted()
            if q.w<0:q.negate()
            values.append(2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w))
        values=np.unwrap(values); values-=round(float(np.median(values))/(2*math.pi))*2*math.pi
        for row,angle in zip(rows,values):
            if abs(angle)>math.radians(210):angle=(angle+math.pi)%(2*math.pi)-math.pi
            for idx,share in ((1,1.),(2,.5)):
                n=f'lowerarm_twist_{idx:02d}_{side}'
                if n in row:
                    local=local_rest[n]
                    row[n]=row[ln]@Matrix.LocRotScale(local.translation,Quaternion(axis,angle*share)@local.to_quaternion(),Vector((1,1,1)))

# Use the established dense exporter, with this task's output names and FPS.
tree=ast.parse((O.parent/'M870Tactical20261015/author_m870.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
code=ast.unparse(node).replace('A_M870_','A_M24_').replace('M870_AUTHORED','M24_AUTHORED').replace('fps = 60','fps = 30').replace('/ 60','/ 30')
authored={}
exec(compile(code,'M24_dense_export','exec'))
for role,rows in clips.items():
    twists(rows); bake(role,rows)
r.animation_data.action=None
for pb in r.pose.bones:pb.matrix_basis=I
s.frame_set(0)
select([r,skin,*parts])
mesh_file=X/'SK_M24_V9.fbx'
bpy.ops.export_scene.fbx(filepath=str(mesh_file),use_selection=True,object_types={'ARMATURE','MESH'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,
    mesh_smooth_type='FACE',use_tspace=True,use_mesh_modifiers=False)
r.animation_data.action=bpy.data.actions['A_M24_idle']; r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=1;s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_V9_Gameplay_Editable.blend'))
report={'mesh':str(mesh_file),'clips':authored,'v9_source':json.loads((O/'V9/template.json').read_text())['mesh'],
        'shape_keys':[k.name for k in skin.data.shape_keys.key_blocks],
        'markers':{n:list(p) for n,p in markers.items()},'fps':30,'runtime_tested':False,
        'newly_authored':['equip','inspect','quick_melee'],'source_retargeted':['fire','reload','cycle','reload_empty']}
(O/'gameplay_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_V9_AUTHORING_COMPLETE',len(authored),'clips',flush=True)
