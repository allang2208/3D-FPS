"""M1911 authoring baseline on the project's accepted Manny arms.

Existing M4 grouped hand poses supply the hand shape; pistol trajectories,
magazine exchange and overhand slide rack are authored here, not downloaded
animation-pack motions. No render or gameplay acceptance is performed.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Euler

O=Path(__file__).parent
S=O.parent
def rows(m): return [list(v) for v in m]
def smooth(t):
    t=max(0.,min(1.,t)); return t*t*t*(t*(t*6-15)+10)
def mix(a,b,t):
    al,aq,asc=a.decompose();bl,bq,bsc=b.decompose()
    if aq.dot(bq)<0: bq.negate()
    return Matrix.LocRotScale(al.lerp(bl,t),aq.slerp(bq,t),asc.lerp(bsc,t))
def track(keys,f):
    if f<=keys[0][0]:return keys[0][1].copy()
    for (a,A),(b,B) in zip(keys,keys[1:]):
        if f<=b:return mix(A,B,smooth((f-a)/(b-a)))
    return keys[-1][1].copy()
def shift(m,v):
    out=m.copy();out.translation+=Vector(v);return out

bpy.ops.wm.open_mainfile(filepath=str(O/'M1911_Source.blend'))
source=bpy.data.objects['M1911'];source_rig=bpy.data.objects['M1911_Rig']
verts=[source.matrix_world@v.co for v in source.data.vertices]
faces=[list(p.vertices) for p in source.data.polygons]
uv=[tuple(l.uv) for l in source.data.uv_layers.active.data]
material_ids=[p.material_index for p in source.data.polygons]
material_names=[m.name for m in source.data.materials]
weights={v.index:max(v.groups,key=lambda g:g.weight).group for v in source.data.vertices if v.groups}
groups={g.index:g.name for g in source.vertex_groups}
source_bones={b.name:source_rig.matrix_world@b.head_local for b in source_rig.data.bones}
part_by_vertex={}
for p in source.data.polygons:
    mat=material_names[p.material_index]
    for i in p.vertices:
        group=groups.get(weights.get(i),'Gun')
        part_by_vertex[i]='WPN_Slide' if mat=='Slide' else 'WPN_Barrel' if mat=='Barrel' else {
            'Gun':'WPN_root','Trigger':'WPN_Trigger','Hammer':'WPN_Hammer',
            'MagRelease':'WPN_MagRelease','SlideRelease':'WPN_SlideRelease',
            'Safety':'WPN_Safety','Mag':'WPN_SOCKET_Magazine',
            'Bullet':'WPN_Bullet','Follower':'WPN_Follower'}.get(group,'WPN_root')

bpy.ops.wm.open_mainfile(filepath=str(S/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export']
def pose(action,f):
    a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    s.frame_set(f);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
base=pose('M4_idle',0);contact=pose('M4_MAT_reload',95)
oldrest={b.name:b.matrix_local.copy() for b in r.data.bones}
parents0={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr0={n:oldrest[parents0[n]].inverted()@m if parents0[n] else m for n,m in oldrest.items()}
contact_basis={n:lr0[n].inverted()@(contact[parents0[n]].inverted()@m if parents0[n] else m) for n,m in contact.items()}
root0=base['WPN_root'];invroot=root0.inverted()
right=invroot@base['hand_r']
left=shift(contact['WPN_root'].inverted()@contact['hand_l'],(-.040,.110,.012))
mag_hand=shift(left,(.012,-.015,-.055))
# Convert the left magazine grasp into an overhand grasp around the slide.
rack=Matrix.Rotation(-math.pi/2,4,'Y')@left
rack.translation=Vector((.035,.110,.105))
for ob in list(s.objects):
    if ob not in [r,hands]:bpy.data.objects.remove(ob,do_unlink=True)
r.animation_data_clear()
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.object.mode_set(mode='EDIT')
# Original pistol faces -X. Project weapon authoring faces -Y, in metres.
xf=Matrix.Translation((0,0,-.020))@Matrix.Rotation(math.pi/2,4,'Z')
points={
    'WPN_Slide':(0,.018,.030),'WPN_Barrel':(0,-.02,.022),
    'WPN_Hammer':tuple(xf@source_bones['Hammer']),
    'WPN_MagRelease':tuple(xf@source_bones['MagRelease']),
    'WPN_SlideRelease':tuple(xf@source_bones['SlideRelease']),
    'WPN_Safety':tuple(xf@source_bones['Safety']),
    'WPN_SOCKET_Magazine':tuple(xf@source_bones['Mag']),
    'WPN_Trigger':tuple(xf@source_bones['Trigger']),
    'WPN_Bullet':tuple(xf@source_bones['Bullet']),
    'WPN_Follower':tuple(xf@source_bones['Follower']),
    'WPN_SOCKET_Muzzle':(0,-.156,.023),
    'WPN_SOCKET_Eject':(-.008,-.009,.034),
    'WPN_RearSight':(0,.046,.045),'WPN_FrontSight':(0,-.139,.0445)}
for n,v in points.items():
    b=r.data.edit_bones.get(n) or r.data.edit_bones.new(n)
    pn='WPN_SOCKET_Magazine' if n in ['WPN_Bullet','WPN_Follower'] else 'WPN_Slide' if n in ['WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Eject'] else 'WPN_root'
    b.parent=r.data.edit_bones[pn];b.use_connect=False
    b.head=oldrest['WPN_root']@Vector(v);b.tail=b.head+Vector((0,0,.015));b.roll=0
bpy.ops.object.mode_set(mode='OBJECT');r.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
names=list(rest);parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
local={n:oldrest['WPN_root'].inverted()@rest[n] for n in names if n.startswith('WPN_')}
for n in names:
    if n not in base:base[n]=root0@local[n]
    elif n in points:base[n]=root0@local[n]
base_basis={n:lr[n].inverted()@(base[parents[n]].inverted()@base[n] if parents[n] else base[n]) for n in names}

me=bpy.data.meshes.new('M1911_Bound')
me.from_pydata([oldrest['WPN_root']@xf@v for v in verts],[],faces);me.update()
for name in material_names:
    mat=bpy.data.materials.new('M_M1911_'+name);mat.diffuse_color=(.13,.06,.028,1) if name=='Grip' else (.08,.085,.095,1);me.materials.append(mat)
layer=me.uv_layers.new(name='UVMap')
for a,b in zip(layer.data,uv):a.uv=b
for p,i in zip(me.polygons,material_ids):p.material_index=i;p.use_smooth=True
gun=bpy.data.objects.new('M1911_Export',me);s.collection.objects.link(gun)
gun.parent=r;gun.matrix_parent_inverse=Matrix.Identity(4);gun.matrix_basis=Matrix.Identity(4)
for n in set(part_by_vertex.values()):gun.vertex_groups.new(name=n).add([i for i,b in part_by_vertex.items() if b==n],1.,'REPLACE')
gun.modifiers.new('M1911_Rig','ARMATURE').object=r

def arm(p,side,H):
    un,fn,hn='upperarm_'+side,'lowerarm_'+side,'hand_'+side
    a,b,c=[base[n].translation.copy() for n in [un,fn,hn]]
    l1=(b-a).length;l2=(c-b).length;goal=H.translation;axis=(goal-a).normalized();d=(goal-a).length
    if d>l1+l2-.002:a+=axis*(d-l1-l2+.002);d=(goal-a).length
    pole=b-a;pole-=axis*pole.dot(axis);pole.normalize()
    along=(l1*l1-l2*l2+d*d)/(2*d);e=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    p['clavicle_'+side].translation+=a-base[un].translation
    for n,pos,direction,orig in [(un,a,e-a,b-base[un].translation),(fn,e,goal-e,c-b)]:
        p[n]=Matrix.LocRotScale(pos,orig.rotation_difference(direction)@base[n].to_quaternion(),base[n].to_scale())
    for n in names:
        if n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):
            pn=un if n.startswith('upperarm') else fn;p[n]=p[pn]@base[pn].inverted()@base[n]
    p[hn]=H
    for n in names:
        if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):
            B=contact_basis[n] if side=='l' else base_basis[n]
            p[n]=p[parents[n]]@lr[n]@B

mag0=local['WPN_SOCKET_Magazine']
def magazine(f):
    if f<42:return track([(0,mag0),(18,mag0),(26,shift(mag0,(0,.012,-.08))),(41,shift(mag0,(.28,.08,-.62))@Matrix.Rotation(1.3,4,'X'))],f)
    return track([(42,shift(mag0,(.17,.1,-.6))),(54,shift(mag0,(.04,.03,-.23))),(65,shift(mag0,(0,.015,-.10))),(78,shift(mag0,(0,.003,-.018))),(84,mag0)],f)
def root_pose(f,kind):
    def R(v,deg):return root0@Matrix.Translation(v)@Euler(tuple(math.radians(x) for x in deg)).to_matrix().to_4x4()
    if kind.startswith('reload'):
        end=156 if kind=='reload_empty' else 108
        return track([(0,root0),(16,R((-.012,.006,.018),(-10,18,0))),(84,R((-.012,.006,.018),(-10,18,0))),(end-20,R((-.010,.004,.012),(-6,12,0))),(end,root0)],f)
    if kind in ['fire','aim_fire','fire_last','aim_fire_last']:
        w=math.sin(min(1,f/9)*math.pi)*math.exp(-f/15) if f<9 else 0
        return R((0,.009*w,0),(-3.5*w,0,0))
    if kind in ['idle','idle_empty']:return shift(root0,(0,0,math.sin(f/180*math.tau)*.00035))
    return root0
clips={};actions={}
spec=[('idle',180),('idle_empty',180),('aim',2),('aim_empty',2),('fire',24),('aim_fire',24),('fire_last',24),('aim_fire_last',24),('reload',108),('reload_empty',156),('equip_charge',54),('equip_charge_empty',54)]
for kind,end in spec:
    samples=[];frames=[i*.5 for i in range(end*2+1)];prev={}
    for f in frames:
        root=root_pose(f,kind);p={n:m.copy() for n,m in base.items()};p['WPN_root']=root
        for n in local:
            if n!='WPN_root':p[n]=root@local[n]
        H=left;slide=0.;barrel=0.
        empty=kind in ['idle_empty','aim_empty','reload_empty']
        if empty:slide=.033
        if kind in ['fire','aim_fire','fire_last','aim_fire_last']:
            if kind.endswith('last'):slide=.033*smooth(f/2)
            else:slide=.036*smooth(f/2)*(1-smooth((f-3)/3))
            barrel=.0025*(slide/.036)
            p['WPN_Trigger']=shift(p['WPN_Trigger'],root.to_quaternion()@Vector((0,.002*smooth(f/2)*(1-smooth((f-4)/4)),0)))
        if kind.startswith('reload'):
            M=magazine(f);p['WPN_SOCKET_Magazine']=root@M
            off=shift(mag_hand,(.15,.09,-.50))
            if f<42:H=track([(0,left),(10,shift(left,(.055,0,0))),(28,off),(42,shift(mag_hand,(.17,.1,-.6)))],f)
            elif f<=88:H=M@mag0.inverted()@mag_hand
            elif kind=='reload':H=track([(88,mag_hand),(96,shift(mag_hand,(.065,0,0))),(108,left)],f)
            else:
                H=track([(88,mag_hand),(96,shift(rack,(.05,0,.035))),(106,shift(rack,(0,.033,0))),(116,shift(rack,(0,.040,0))),(122,shift(rack,(0,.040,0))),(124,rack),(134,shift(rack,(.06,0,.05))),(156,left)],f)
                slide=.033+.007*smooth((f-106)/10) if f<122 else .040*(1-smooth((f-122)/2))
        if kind.startswith('equip_charge'):
            H=track([(0,left),(10,shift(rack,(.05,0,.035))),(20,rack),(28,shift(rack,(0,.040,0))),(32,shift(rack,(0,.040,0))),(34,rack),(42,shift(rack,(.06,0,.05))),(54,left)],f)
            slide=.04*smooth((f-20)/8)*(1-smooth((f-32)/2))
            if kind=='equip_charge_empty':slide=.033+.007*smooth((f-20)/8)*(1-smooth((f-32)/2))
        p['WPN_Slide']=shift(root@local['WPN_Slide'],root.to_quaternion()@Vector((0,slide,0)))
        p['WPN_Barrel']=shift(root@local['WPN_Barrel'],root.to_quaternion()@Vector((0,barrel,-barrel)))
        for n in ['WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Eject']:p[n]=p['WPN_Slide']@lr[n]
        for n in ['WPN_Bullet','WPN_Follower']:p[n]=p['WPN_SOCKET_Magazine']@lr[n]
        if kind in ['idle_empty','aim_empty'] or kind=='reload_empty' and f<42:
            p['WPN_Bullet']=shift(p['WPN_Bullet'],root.to_quaternion()@Vector((0,0,-.065)))
        arm(p,'r',root@right);arm(p,'l',root@H)
        row={}
        for n in names:
            B=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,scale=B.decompose()
            if n in prev and prev[n].dot(q)<0:q.negate()
            prev[n]=q.copy();row[n]=(loc,q,scale)
        samples.append(row)
    a=bpy.data.actions.new('M1911_'+kind);a.use_fake_user=True;r.animation_data.action=a
    for n in names:
        b=r.pose.bones[n];b.rotation_mode='QUATERNION'
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
    bag=a.layers[0].strips[0].channelbag(a.slots[0]);curves={(fc.data_path,fc.array_index):fc for fc in bag.fcurves}
    for n in names:
        for prop,idx,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                fc=curves[(f'pose.bones["{n}"].{prop}',axis)]
                fc.keyframe_points.clear();fc.keyframe_points.add(len(frames))
                fc.keyframe_points.foreach_set('co',[v for f,row in zip(frames,samples) for v in (f,row[n][idx][axis])])
                for k in fc.keyframe_points:k.interpolation='LINEAR'
                fc.update()
    r.animation_data.action_slot=a.slots[0];s.render.fps=60;s.frame_start=0;s.frame_end=end
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(O/f'A_M1911_{kind}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
    actions[kind]=a;clips[kind]={'frames':end,'fps':60,'sample_rate':120,'duration':end/60,'loop':kind.startswith('idle')}
r.animation_data.action=actions['idle'];r.animation_data.action_slot=actions['idle'].slots[0];s.frame_set(0);s.frame_end=180
bpy.ops.object.select_all(action='DESELECT')
for ob in [r,hands,gun]:ob.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'SK_M1911_Manny.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_Manny_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':clips,'markers':points,'source':'Xeradev M1911 FBX; existing Manny mesh and grouped hand poses','animation_status':'Locally authored pistol baseline; not a mature GitHub animation pack; not playtested','contacts_frames':{'reload':[18,78,84],'reload_empty':[18,78,84,116,124],'equip_charge':[28,34]}},indent=2))
print('M1911_AUTHORING_COMPLETE')
