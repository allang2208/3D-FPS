"""Author the supplied 715 on the existing Manny skin; bake game animation assets.

Reference: M1911 Contact/P9 idle, aim, recoil and draw; new revolver reload.
All geometry remains at the source's metre scale. No render or gameplay test.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion, Euler

O=Path(__file__).parent
import sys
sys.path.insert(0,str(O))
from fbx_bind_pose import install
install()
(O/'Animations').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
try:
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911Contact20260913/M1911_Contact_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error) or 'SK_M1911_Manny' not in bpy.data.objects:raise
oldrig=bpy.data.objects['SK_M1911_Manny']
oldhands=bpy.data.objects['SK_Manny_Arms_Export']
scene=bpy.context.scene
source_names=['idle','aim','fire','aim_fire','equip_charge','reload','reload_empty','inspect']
donors={}
# Read the existing actions before changing the skeleton; retain source poses
# and times, including the magazine-contact reference for arm reach.
for kind in source_names:
    action=bpy.data.actions['M1911_Contact_'+kind]
    oldrig.animation_data.action=action;oldrig.animation_data.action_slot=action.slots[0]
    duration=float(action.frame_range[1])/60
    rows=[]
    for index in range(round(duration*120)+1):
        f=index*.5;scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
        rows.append({b.name:b.matrix.copy() for b in oldrig.pose.bones})
    donors[kind]={'duration':duration,'poses':rows}
newscene=bpy.data.scenes.new('DanWesson715_Authoring');bpy.context.window.scene=newscene;scene=newscene
rig=oldrig.copy();rig.data=oldrig.data.copy();rig.animation_data_clear();scene.collection.objects.link(rig)
hands=oldhands.copy();hands.data=oldhands.data.copy();scene.collection.objects.link(hands)
hands.parent=rig;hands.matrix_parent_inverse=Matrix.Identity(4);hands.matrix_basis=Matrix.Identity(4)
for mod in hands.modifiers:
    if mod.type=='ARMATURE':mod.object=rig
for ob in list(bpy.data.objects):
    if ob not in (rig,hands):bpy.data.objects.remove(ob,do_unlink=True)
for other in list(bpy.data.scenes):
    if other!=scene:bpy.data.scenes.remove(other)
rig.name='SK_DW715_Manny';hands.name='SK_Manny_Arms_Export'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.render.fps=60
rig.hide_set(False);rig.data.pose_position='POSE'
for b in rig.pose.bones:
    b.matrix_basis=Matrix.Identity(4)
    for c in list(b.constraints):b.constraints.remove(c)
root=rig.data.bones['WPN_root'].matrix_local.copy()
shift=Vector((0,-.0855,.035))
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(next((O/'Original').rglob('DW_model715.FBX'))))
imported=list(set(bpy.data.objects)-before)
original={ob.name:ob for ob in imported}
world={ob.name:ob.matrix_world.copy() for ob in imported}
geometry=json.loads((O/'source-geometry.json').read_text())
assembly=next(ob for ob in geometry['objects'] if ob['name']=='DW_MagazineAssembly')
islands=assembly['islands']
local={}
parents={}
def bone(name,point,parent='WPN_root'):
    local[name]=Matrix.Translation(Vector(point)+shift);parents[name]=parent
bone('WPN_Crane',(.006714,.005753,-.031319))
bone('WPN_Cylinder',(0,.03705,-.00408),'WPN_Crane')
bone('WPN_Extractor',(0,.0585,-.00408),'WPN_Cylinder')
bone('WPN_Loader',(0,.085,-.00408))
bone('WPN_Hammer',(-.00017,.077,-.004))
bone('WPN_Trigger',(-.00011,.05055,-.03665))
bone('WPN_SOCKET_Muzzle',(0,-.13928,.0081))
bone('WPN_SOCKET_Eject',(0,.059,-.00408),'WPN_Crane')
bone('WPN_RearSight',(0,.078,.0290))
bone('WPN_FrontSight',(0,-.127,.0290))
bone('WPN_SOCKET_Magazine',(0,.03705,-.00408),'WPN_Crane')
for n in range(6):
    center=world[f'DW_Bullet_{n}'].translation
    bone(f'WPN_Case_{n}',center,'WPN_Cylinder')
    bone(f'WPN_Round_{n}',center,f'WPN_Case_{n}')
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name,L in local.items():
    eb=rig.data.edit_bones.get(name) or rig.data.edit_bones.new(name)
    eb.parent=rig.data.edit_bones[parents[name]];eb.use_connect=False
    eb.matrix=root@L;eb.length=.018
bpy.ops.object.mode_set(mode='OBJECT')
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
names=[]
def add(n):
    if n in names:return
    if parent[n]:add(parent[n])
    names.append(n)
for n in rest:add(n)
lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
gunlocal={n:root.inverted()@rest[n] for n in names if n.startswith('WPN_')}
gunmeshes=[]
surface=bpy.data.materials.new('M_DW715_Surface');surface.use_nodes=True
bsdf=next(n for n in surface.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
texroot=next((O/'Original').rglob('Base Set Semi Dmg'))
for suffix,channel in [('AlbedoTransparency','Base Color'),('Normal','Normal')]:
    tex=surface.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(texroot/f'DW_Set0_SemiDmg_{suffix}.png'))
    if suffix=='Normal':
        tex.image.colorspace_settings.name='Non-Color';normal=surface.node_tree.nodes.new('ShaderNodeNormalMap');surface.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);surface.node_tree.links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
    else:surface.node_tree.links.new(tex.outputs['Color'],bsdf.inputs[channel])
packed=surface.node_tree.nodes.new('ShaderNodeTexImage');packed.image=bpy.data.images.load(str(texroot/'DW_Set0_SemiDmg_MetallicSmoothness.png'));packed.image.colorspace_settings.name='Non-Color'
sep=surface.node_tree.nodes.new('ShaderNodeSeparateColor');surface.node_tree.links.new(packed.outputs['Color'],sep.inputs['Color']);surface.node_tree.links.new(sep.outputs['Red'],bsdf.inputs['Metallic'])
inv=surface.node_tree.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;surface.node_tree.links.new(packed.outputs['Alpha'],inv.inputs[1]);surface.node_tree.links.new(inv.outputs[0],bsdf.inputs['Roughness'])
def bind(ob,assignments):
    transform=root@Matrix.Translation(shift)@world[ob.name]
    ob.data.transform(transform);ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    ob.vertex_groups.clear()
    for bn,ids in assignments.items():
        if ids:ob.vertex_groups.new(name=bn).add(list(ids),1,'REPLACE')
    ob.data.materials.clear();ob.data.materials.append(surface)
    mod=ob.modifiers.new('Manny_Weapon_Skin','ARMATURE');mod.object=rig
    ob['source_object']=ob.name;gunmeshes.append(ob)
for ob in imported:
    if ob.type!='MESH':continue
    if ob.name=='DW_MagazineAssembly':
        assignments={'WPN_Cylinder':islands[0]['ids'],'WPN_Crane':islands[1]['ids']+islands[2]['ids'],'WPN_Extractor':[v for i in islands[3:] for v in i['ids']]}
    elif ob.name.startswith('DW_Bullet_'):
        n=int(ob.name.rsplit('_',1)[1]);assignments={f'WPN_Case_{n}':[],f'WPN_Round_{n}':[]}
        for v in ob.data.vertices:
            point=world[ob.name]@v.co
            assignments[f'WPN_Round_{n}' if point.y<.0235 else f'WPN_Case_{n}'].append(v.index)
    else:assignments={{'DW_Hummer':'WPN_Hammer','DW_Trigger':'WPN_Trigger'}.get(ob.name,'WPN_root'):list(range(len(ob.data.vertices)))}
    bind(ob,assignments)
for ob in imported:
    if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True)
# An authored loader is a reload prop, never a permanently attached magazine.
loader_mat=bpy.data.materials.new('M_DW715_Loader');loader_mat.diffuse_color=(.024,.028,.033,1)
loader_mat.use_nodes=True;loader_bsdf=next(n for n in loader_mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
loader_bsdf.inputs['Base Color'].default_value=(.024,.028,.033,1)
loader_bsdf.inputs['Roughness'].default_value=.48
bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.020,depth=.025,rotation=(math.pi/2,0,0))
loader=bpy.context.object;loader.name='DW715_Speedloader'
loader.matrix_world=Matrix.Translation(Vector((0,.085,-.00408)))@loader.rotation_euler.to_matrix().to_4x4()
world[loader.name]=loader.matrix_world.copy();bind(loader,{'WPN_Loader':list(range(len(loader.data.vertices)))})
loader.data.materials.clear();loader.data.materials.append(loader_mat)

def smooth(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
def mix(a,b,t):
    return Matrix.LocRotScale(a.translation.lerp(b.translation,t),a.to_quaternion().slerp(b.to_quaternion(),t),a.to_scale().lerp(b.to_scale(),t))
def source(kind,t):return {n:m.copy() for n,m in donors[kind]['poses'][min(round(max(0,t)*120),len(donors[kind]['poses'])-1)].items()}
def hand_at(p,old,side,H):
    hn='hand_'+side;delta=H@old[hn].inverted()
    for n in names:
        if n==hn or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n]=delta@old[n]
    un,fn='upperarm_'+side,'lowerarm_'+side
    shoulder=old[un].translation.copy();elbow=old[fn].translation;wrist=old[hn].translation;target=H.translation
    l1=(elbow-shoulder).length;l2=(wrist-elbow).length;v=target-shoulder;distance=v.length;axis=v.normalized()
    reach=(l1+l2)*.985
    if distance>reach:shoulder+=axis*(distance-reach);distance=reach
    distance=max(abs(l1-l2)+.0001,distance)
    pole=elbow-old[un].translation;pole-=axis*pole.dot(axis)
    if pole.length<1e-6:pole=Vector((0,0,-1))-axis*axis.dot(Vector((0,0,-1)))
    pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    e=shoulder+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    p['clavicle_'+side]=old['clavicle_'+side].copy()
    p['clavicle_'+side].translation+=shoulder-old[un].translation
    for n,pos,direction,was in [(un,shoulder,e-shoulder,elbow-old[un].translation),(fn,e,target-e,wrist-elbow)]:
        p[n]=Matrix.LocRotScale(pos,was.rotation_difference(direction)@old[n].to_quaternion(),old[n].to_scale())
    for n in names:
        if n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):
            base=un if n.startswith('upperarm') else fn;p[n]=p[base]@old[base].inverted()@old[n]
    if 'ik_hand_'+side in p:p['ik_hand_'+side]=H.copy()

idle=source('idle',0)
leftlocal=idle['WPN_root'].inverted()@idle['hand_l']
durations={'idle':3.,'aim':1/30,'fire':.4,'aim_fire':.4,'equip_charge':donors['equip_charge']['duration'],'reload':3.2,'reload_empty':3.45,'inspect':donors['inspect']['duration']}
events={'open':.40,'eject':.82,'loader_insert':1.92,'rounds_seat':2.15,'close':2.73,'ready':3.2}
def pose(kind,t):
    reload=kind.startswith('reload');isfire=kind in ('fire','aim_fire')
    sourcekind='idle' if reload else kind
    old=source(sourcekind,t*(donors[kind]['duration']/.4) if isfire else t)
    p={n:old.get(n,rest[n]).copy() for n in names};G=old['WPN_root'].copy()
    u=t*(3.2/durations[kind]) if reload else t
    if reload:
        weight=smooth(u/.36)*(1-smooth((u-2.78)/.42))
        turn=Euler((math.radians(-27)*weight,math.radians(-32)*weight,math.radians(13)*weight),'XYZ').to_quaternion()
        G=G@Matrix.LocRotScale(Vector((.035,.065,.022))*weight,turn,Vector((1,1,1)))
        d=G@old['WPN_root'].inverted()
        for n in names:
            if n in old:p[n]=d@old[n]
        hand_at(p,old,'r',d@old['hand_r'])
    p['WPN_root']=G
    for n,L in gunlocal.items():
        if n!='WPN_root':p[n]=G@L
    p['WPN_Loader']=G@gunlocal['WPN_Loader']@Matrix.Diagonal((.0001,.0001,.0001,1))
    if isfire:
        # Sixfold cylinder symmetry permits a clean next-shot/idle boundary.
        p['WPN_Cylinder']=G@gunlocal['WPN_Cylinder']@Matrix.Rotation(math.radians(60)*smooth(u/.045),4,'Y')
        pull=smooth(u/.018)*(1-smooth((u-.085)/.11))
        p['WPN_Trigger']=G@gunlocal['WPN_Trigger']@Matrix.Rotation(-.24*pull,4,'X')
        p['WPN_Hammer']=G@gunlocal['WPN_Hammer']@Matrix.Rotation(-.45*(1-smooth(u/.035)),4,'X')
    if reload:
        opened=smooth((u-.18)/.25)*(1-smooth((u-2.50)/.23))
        crane=G@gunlocal['WPN_Crane']@Matrix.Rotation(math.radians(-78)*opened,4,'Y')
        p['WPN_Crane']=crane
        p['WPN_Cylinder']=crane@gunlocal['WPN_Crane'].inverted()@gunlocal['WPN_Cylinder']
        p['WPN_SOCKET_Magazine']=crane@gunlocal['WPN_Crane'].inverted()@gunlocal['WPN_SOCKET_Magazine']
        p['WPN_SOCKET_Eject']=crane@gunlocal['WPN_Crane'].inverted()@gunlocal['WPN_SOCKET_Eject']
        lift=smooth((u-.67)/.15)*(1-smooth((u-.90)/.18))
        p['WPN_Extractor']=p['WPN_Cylinder']@gunlocal['WPN_Cylinder'].inverted()@gunlocal['WPN_Extractor']@Matrix.Translation((0,.023*lift,0))
        cyl_delta=p['WPN_Cylinder']@gunlocal['WPN_Cylinder'].inverted()
        approach=Vector((-.08,.20,-.23)).lerp(Vector((0,.018,0)),smooth((u-1.20)/.72))
        if u>=1.92:approach=Vector((0,.018*(1-smooth((u-1.92)/.23)),0))
        if u>=2.18:approach=Vector((-.08,.16,-.20))*smooth((u-2.18)/.32)
        loaderframe=cyl_delta@Matrix.Translation(approach)@gunlocal['WPN_Loader']
        if 1.10<=u<=2.5:p['WPN_Loader']=loaderframe
        # Left hand first opens the crane, presses the ejector, then retrieves
        # a loader below frame, inserts axially, releases and closes the crane.
        hold=p['WPN_Cylinder'].copy();hold.translation+=G.to_quaternion()@Vector((-.045,.015,-.015))
        hold=Matrix.LocRotScale(hold.translation,(G@leftlocal).to_quaternion(),Vector((1,1,1)))
        eject=hold.copy();eject.translation+=G.to_quaternion()@Vector((.01,-.045,.018))
        loaderhand=loaderframe@Matrix.Translation((-.03,.012,-.024));loaderhand=Matrix.LocRotScale(loaderhand.translation,(G@leftlocal).to_quaternion(),Vector((1,1,1)))
        support=G@leftlocal
        if u<.4:H=mix(support,hold,smooth(u/.4))
        elif u<.82:H=mix(hold,eject,smooth((u-.4)/.42))
        elif u<1.12:H=mix(eject,loaderhand,smooth((u-.82)/.30))
        elif u<2.42:H=loaderhand
        elif u<2.66:H=mix(loaderhand,hold,smooth((u-2.42)/.24))
        else:H=mix(hold,support,smooth((u-2.66)/.48))
        hand_at(p,old,'l',H)
        for n in range(6):
            bn=f'WPN_Case_{n}'
            C=cyl_delta@gunlocal[bn]
            if .68<=u<1.02:
                amount=smooth((u-.68)/.14);fall=max(0,u-.82)
                C.translation+=G.to_quaternion()@Vector((-.02*fall,.034*amount+.10*fall,-1.5*fall*fall))
            elif 1.02<=u<1.20:C=C@Matrix.Diagonal((.0001,.0001,.0001,1))
            elif 1.20<=u<2.15:
                offset=Vector((-.08,.20,-.23)).lerp(Vector((0,.018,0)),smooth((u-1.20)/.72)) if u<1.92 else Vector((0,.018*(1-smooth((u-1.92)/.23)),0))
                C=cyl_delta@Matrix.Translation(offset)@gunlocal[bn]
            p[bn]=C;p[f'WPN_Round_{n}']=C@gunlocal[bn].inverted()@gunlocal[f'WPN_Round_{n}']
    else:
        for n in ['WPN_Extractor']+[f'WPN_Case_{i}' for i in range(6)]+[f'WPN_Round_{i}' for i in range(6)]:
            p[n]=p[parent[n]]@lr[n]
    return p

actions={}
for kind,duration in durations.items():
    frames=[i*.5 for i in range(round(duration*120)+1)];samples=[];previous={}
    for f in frames:
        p=pose(kind,f/60);row={}
        for n in names:
            basis=lr[n].inverted()@(p[parent[n]].inverted_safe()@p[n] if parent[n] else p[n])
            loc,q,scale=basis.decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        samples.append(row)
    action=bpy.data.actions.new('DW715_'+kind);action.use_fake_user=True;rig.animation_data_create();rig.animation_data.action=action
    for n in names:
        b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
    for n in names:
        for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(frames))
                c.keyframe_points.foreach_set('co',[v for f,row in zip(frames,samples) for v in (f,row[n][field][axis])])
                for key in c.keyframe_points:key.interpolation='LINEAR'
                c.update()
    rig.animation_data.action_slot=action.slots[0];scene.frame_start=0;scene.frame_end=round(duration*60);scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(O/'Animations'/f'A_DW715_{kind}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
    actions[kind]=action;print('DW715_AUTHORED',kind,flush=True)
rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
for ob in [rig,hands]+gunmeshes:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_DW715_Manny.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
rig.animation_data_create();rig.animation_data.action=actions['idle'];rig.animation_data.action_slot=actions['idle'].slots[0];scene.frame_start=0;scene.frame_end=180;scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_Manny_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'durations':durations,'normal_events':events,'empty_event_scale':3.45/3.2,'sample_rate':120,'source_grip_shift_m':list(shift),'mechanical_parents':parents,'reference':'M1911Contact20260913 / Infima P9; revolver reload newly authored','testing':'Not run; user testing pending'},indent=2))
print('DW715_AUTHORING_COMPLETE',flush=True)
