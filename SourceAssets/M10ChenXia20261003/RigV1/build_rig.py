"""Create the original-mesh rig, surface weights and authored clips in Blender."""
from pathlib import Path
import json,math
import bpy
import numpy as np
from mathutils import Vector,Matrix,Quaternion
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Delivery';OUT.mkdir(exist_ok=True)
cfg=json.loads((ROOT/'rig_definition.json').read_text(encoding='utf-8'))
weights=np.load(ROOT/'authored_weights.npz')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.;scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(ROOT/'M10_Meshy_original.glb'))
obj=next(o for o in scene.objects if o.type=='MESH');obj.name='M10_OriginalSurface';obj.data.name='M10_Meshy_Surface'
transform=Matrix.Rotation(math.pi/2,4,'Z')@obj.matrix_world
points=np.array([tuple(transform@v.co) for v in obj.data.vertices]);lo=points.min(axis=0);hi=points.max(axis=0)
scale=4.2/(hi[0]-lo[0]);offset=Vector((-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]))
transform=Matrix.Scale(scale,4)@Matrix.Translation(offset)@transform
norm=transform.to_3x3().inverted().transposed()
custom=[(norm@Vector(n.vector)).normalized() for n in obj.data.corner_normals]
obj.data.transform(transform);obj.matrix_world=Matrix.Identity(4);obj.data.normals_split_custom_set(custom)
arm=bpy.data.armatures.new('M10_CustomEightLimbSkeleton');rig=bpy.data.objects.new('Armature',arm);scene.collection.objects.link(rig)
rig.show_in_front=True;arm.display_type='OCTAHEDRAL'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for spec in cfg['bones']:
    b=arm.edit_bones.new(spec['name']);b.head=spec['head'];b.tail=spec['tail'];b.use_deform=spec['deform']
    if spec['parent']:b.parent=arm.edit_bones[spec['parent']];b.use_connect=(b.head-b.parent.tail).length<1e-6
    b.align_roll(Vector((0,1,0)))
bpy.ops.object.mode_set(mode='OBJECT')
for label in sorted({b['region'] for b in cfg['bones']}):
    col=arm.collections.new(label)
    for spec in cfg['bones']:
        if spec['region']==label:col.assign(arm.bones[spec['name']])
kd=KDTree(len(weights['vertices']))
for i,p in enumerate(weights['vertices']):kd.insert(Vector(p),i)
kd.balance(); mapping=np.array([kd.find(v.co)[1] for v in obj.data.vertices])
indices=weights['bone_indices'][mapping];values=weights['weights'][mapping];names=weights['bone_names']
groups=[obj.vertex_groups.new(name=str(name)) for name in names]
for i in range(len(obj.data.vertices)):
    for j in range(4):
        if values[i,j]>1e-6:groups[indices[i,j]].add([i],float(values[i,j]),'REPLACE')
mod=obj.modifiers.new('M10_DedicatedSurfaceSkin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False;obj.parent=rig
print('M10_SKIN_BOUND',len(obj.data.vertices),'vertices',len(arm.bones),'bones',flush=True)

rest={b.name:b.matrix_local.copy() for b in arm.bones};rig.animation_data_create()
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def envelope(t,a,b,c):return smooth((t-a)/(b-a))*(1-smooth((t-b)/(c-b)))
def aim(name,head,tail):
    old=Vector(arm.bones[name].tail_local-arm.bones[name].head_local);new=tail-head
    q=old.rotation_difference(new)
    return Matrix.Translation(head)@q.to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()
def ik(root,knee,ankle,target):
    upper=(knee-root).length;lower=(ankle-knee).length;delta=target-root
    distance=max(abs(upper-lower)+.001,min(delta.length,upper+lower-.001));direction=delta.normalized()
    plane=knee-root;plane-=direction*plane.dot(direction)
    if plane.length<.001:plane=Vector((0,1 if knee.y>0 else -1,0))
    plane.normalize();along=(upper*upper-lower*lower+distance*distance)/(2*distance)
    height=math.sqrt(max(0,upper*upper-along*along))
    return root+direction*along+plane*height,root+direction*distance
def poses(role,t,duration):
    out={n:m.copy() for n,m in rest.items()};phase=2*math.pi*t/duration
    breath=.006*math.sin(phase);body_shift=Vector((0,0,breath if role=='Idle' else 0))
    recoil=envelope(t,0,.12,.65) if role=='Hit' else 0
    strike=envelope(t,.45,.85,1.22) if role=='Bite' else 0
    dying=smooth(t/1.35) if role=='Death' else 0
    for name in ['body_center','body_front','body_rear','rump','head']:
        p=rest[name].translation.copy();front=smooth((p.x+.6)/2.)
        shift=body_shift+Vector((.065*strike*front-.045*recoil*front,0,-.025*recoil*front-.02*dying))
        if role=='Walk':shift+=Vector((.008*math.sin(phase*2-p.x),.008*math.sin(phase),.008*(1+math.sin(phase*2))))
        out[name]=Matrix.Translation(shift)@rest[name]
    for spec in cfg['bones']:
        if spec['region']!='mantle':continue
        name=spec['name'];parent=spec['parent'];out[name]=out[parent]@rest[parent].inverted()@rest[name]
        flutter=(.007*math.sin(phase+spec['head'][0])) if role in ('Idle','Walk') else 0
        out[name]=Matrix.Translation(Vector((0,0,flutter)))@out[name]
    jaw_angle=0
    if role=='Idle':jaw_angle=math.radians(1.2)*math.sin(phase)
    if role=='Bite':jaw_angle=math.radians(11)*envelope(t,0,.5,.75)-math.radians(16)*envelope(t,.64,.85,1.18)
    if role=='Hit':jaw_angle=math.radians(3)*recoil
    if role=='Death':jaw_angle=math.radians(7)*dying
    jaw_rest=out['head']@rest['head'].inverted()@rest['jaw'];out['jaw']=Matrix.Translation(jaw_rest.translation)@Quaternion((0,1,0),jaw_angle).to_matrix().to_4x4()@jaw_rest.to_3x3().to_4x4()
    out['mouth_socket']=out['head']@rest['head'].inverted()@rest['mouth_socket']
    for leg in cfg['legs']:
        points=[Vector(p) for p in leg['points']];root,knee,ankle,toe=points
        root=out[leg['parent']]@rest[leg['parent']].inverted()@root;target=ankle.copy();lift=0
        if role=='Walk':
            offset=[0.,.5,.25,.75][leg['pair']-1]+(.5 if leg['side']=='R' else 0)
            ph=(t/duration+offset)%1.;stance=.65
            if ph<stance:dx=.18-.36*ph/stance
            else:
                q=(ph-stance)/(1-stance);dx=-.18+.36*smooth(q);lift=.085*math.sin(math.pi*q)**2
            target+=Vector((dx,0,lift))
        if role=='Death':target+=Vector((-.025*dying,0,.015*dying))
        joint,end=ik(root,knee,ankle,target)
        upper,lower,foot=leg['bones'];out[upper]=aim(upper,root,joint);out[lower]=aim(lower,joint,end)
        out[foot]=aim(foot,end,toe+(end-ankle))
        for sector in ('inner','outer'):
            name=leg['region']+'_toes_'+sector;out[name]=out[foot]@rest[foot].inverted()@rest[name]
    return out

contracts={'Idle':3.2,'Walk':1.2,'Bite':1.5,'Hit':.65,'Death':2.5}
clips={}
for role,duration in contracts.items():
    action=bpy.data.actions.new('M10_'+role);action.use_fake_user=True;rig.animation_data.action=action
    count=round(duration*30);duration=count/30
    for f in range(count+1):
        scene.frame_set(f+1);targets=poses(role,f/30,duration)
        for b in arm.bones:
            local=rest[b.name].inverted()@rest[b.parent.name]@targets[b.parent.name].inverted()@targets[b.name] if b.parent else rest[b.name].inverted()@targets[b.name]
            p=rig.pose.bones[b.name];p.rotation_mode='QUATERNION';p.matrix_basis=local
            p.keyframe_insert('location',frame=f+1);p.keyframe_insert('rotation_quaternion',frame=f+1);p.keyframe_insert('scale',frame=f+1)
        if not rig.animation_data.action_slot and action.slots:rig.animation_data.action_slot=action.slots[0]
    clips[role]={'seconds':duration,'frames':count+1,'loop':role in ('Idle','Walk'),'action':action.name,'file':str(OUT/f'A_M10_{role}.fbx')}
    print('M10_CLIP_AUTHORED',role,flush=True)
for im in bpy.data.images:
    if im.has_data and im.source=='FILE':im.pack()
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
scene.frame_start=1;scene.frame_end=97;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M10_Rigged_Editable.blend'))
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
export=dict(use_selection=True,path_mode='AUTO',add_leaf_bones=False,use_armature_deform_only=False,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_M10_Mawcrawler.fbx'),bake_anim=False,**export)
# Animation-only FBX avoids repeating the 1.3M-triangle skin for each clip.
obj.select_set(False)
for role,row in clips.items():
    a=bpy.data.actions[row['action']];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    scene.frame_end=row['frames'];scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=row['file'],bake_anim=True,**export)
rig.animation_data.action=bpy.data.actions['M10_Idle'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_end=97;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M10_Rigged_Editable.blend'))
(ROOT/'animation_contract.json').write_text(json.dumps({'clips':clips,'walk_source_speed_cm_s':46.153846,'bite_contact_seconds':.85,'death_handoff_fraction':.6,'bones':len(arm.bones),'original_triangles':1299090,'lods_authored':False,'weight_influences':4,'runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
print('M10_RIG_AND_CLIPS_SAVED',str(OUT),flush=True)
