"""Rigid hardware islands and a planted, forward trunk slam on the existing rig."""
from pathlib import Path
import bpy, numpy as np, json, math, struct
from mathutils import Vector, Quaternion, kdtree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004');OUT=ROOT/'ProductionV11'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ProductionV08/Authoring/M14_Rigged_Bite_v08.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['M14_Rig'];obj=bpy.data.objects['M14_SoftDeathMesh'];mesh=obj.data
rig.animation_data.action=None
for b in rig.pose.bones:b.location=(0,0,0);b.rotation_quaternion=(1,0,0,0);b.scale=(1,1,1)
scene.frame_set(0)
d=np.load(OUT/'Records/hardware_source.npz');comp=np.load(OUT/'Records/hardware_components.npz')
p=d['p'];faces=d['f'];metal=d['metal'];fc=comp['metal_face_components'];groups=[g.name for g in obj.vertex_groups]
metal_groups={i for i,name in enumerate(groups) if name.startswith('chain_') or name=='restraint'}
is_metal=np.zeros(len(p),bool);is_metal[np.unique(faces[metal])]=True
old_b=np.full((len(p),4),-1,np.int32);old_w=np.zeros((len(p),4),np.float32)
for i,v in enumerate(mesh.vertices):
    for j,g in enumerate(sorted(v.groups,key=lambda g:-g.weight)[:4]):old_b[i,j]=g.group;old_w[i,j]=g.weight
new_b=old_b.copy();new_w=old_w.copy()
shape_names=['M14_DeathSag','M14_DeathFold','M14_DeathSpread'];shapes=[]
if mesh.shape_keys.animation_data:mesh.shape_keys.animation_data_clear()
for name in shape_names:
    key=mesh.shape_keys.key_blocks[name];key.value=0
    q=np.empty(len(p)*3,np.float32);key.data.foreach_get('co',q);shapes.append(q.reshape(-1,3))
mf=faces[metal];islands=[]
for cid in range(len(comp['component_sizes'])):
    ids=np.unique(mf[fc==cid]);points=p[ids];center=points.mean(0)
    scores=np.zeros(len(groups),np.float64)
    for j in range(4):
        good=np.isin(old_b[ids,j],list(metal_groups))
        np.add.at(scores,old_b[ids[good],j],old_w[ids[good],j])
    bone=int(scores.argmax())
    if scores[bone]<=0:
        candidates=[groups.index('chain_'+('L' if center[0]>0 else 'R')+'_'+str(i)) for i in range(3)]
        bone=min(candidates,key=lambda i:(Vector(center)-rig.data.bones[groups[i]].head_local).length)
    new_b[ids]=-1;new_b[ids,0]=bone;new_w[ids]=0;new_w[ids,0]=1
    # Each metal island follows the old collapse trajectory as a rigid object.
    # Fit rotation/translation only; never squash metal with the tissue field.
    for q in shapes:
        dest=q[ids].copy();dest_center=dest.mean(0)
        if len(ids)>=3:
            a,_,bt=np.linalg.svd((points-center).T@(dest-dest_center))
            rot=a@bt
            if np.linalg.det(rot)<0:a[:,-1]*=-1;rot=a@bt
            rigid=(points-center)@rot+dest_center
        else:rigid=points-center+dest_center
        rigid[:,2]+=max(0.,.012-float(rigid[:,2].min()))
        q[ids]=rigid
    islands.append({'component':cid,'vertices':len(ids),'triangles':int(comp['component_sizes'][cid]),'bone':groups[bone]})
# Remove leaked metal influences from the tissue on the other side of the cut.
leak=(~is_metal)&np.any(np.isin(old_b,list(metal_groups))&(old_w>.0001),axis=1)
clean=np.flatnonzero((~is_metal)&~leak)
tree=kdtree.KDTree(len(clean))
for i in clean:tree.insert(p[i],int(i))
tree.balance()
for i in np.flatnonzero(leak):
    _,nearest,_=tree.find(p[i]);new_b[i]=old_b[nearest];new_w[i]=old_w[nearest]
changed=np.flatnonzero(is_metal|leak)
for g in obj.vertex_groups:g.remove(changed.tolist())
for slot in range(4):
    active=changed[new_w[changed,slot]>0]
    keys=new_b[active,slot].astype(np.int64)*65536+np.rint(new_w[active,slot]*65535).astype(np.int64)
    order=np.argsort(keys);active=active[order];keys=keys[order]
    values,starts=np.unique(keys,return_index=True);ends=np.r_[starts[1:],len(keys)]
    for value,start,end in zip(values,starts,ends):
        obj.vertex_groups[int(value//65536)].add(active[start:end].tolist(),float(value%65536)/65535,'REPLACE')
for name,q in zip(shape_names,shapes):mesh.shape_keys.key_blocks[name].data.foreach_set('co',q.ravel())
payload=np.zeros((len(changed),21),np.float32);payload[:,:3]=p[changed];payload[:,3]=is_metal[changed]
payload[:,4:8]=new_b[changed];payload[:,8:12]=new_w[changed]
for j,q in enumerate(shapes):payload[:,12+3*j:15+3*j]=q[changed]-p[changed]
with (OUT/'Exports/hardware_skin.bin').open('wb') as out:
    out.write(struct.pack('<i',len(payload)));out.write(payload.astype('<f4').tobytes())
(OUT/'Exports/hardware_bones.json').write_text(json.dumps(groups),encoding='utf8')

def ease(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
def pulse(t,a,b,c):return ease((t-a)/(b-a)) if t<b else 1-ease((t-b)/(c-b))
def turn(name,axis,angle):
    pb=rig.pose.bones[name];pb.rotation_quaternion=Quaternion(pb.bone.matrix_local.to_3x3().inverted()@Vector(axis),angle)
def shift(name,v):rig.pose.bones[name].location=rig.data.bones[name].matrix_local.to_3x3().inverted()@Vector(v)
name='A_M14_TrunkSlam_v11';action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
scene.render.fps=30;scene.frame_start=0;scene.frame_end=96
for frame in range(97):
    scene.frame_set(frame);t=frame/30
    for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
    wind=ease(t/.80)*(1-ease((t-.80)/.32))
    fall=ease((t-.80)/.40)*(1-ease((t-1.48)/1.60))
    rebound=pulse(t,1.20,1.30,1.48)
    turn('base',(1,0,0),1.10*fall-.065*wind-.035*rebound)
    shift('base',(0,0,-.075*fall))
    for k,angle in enumerate((.37,.16,.035,-.025,-.02),1):
        turn(f'spine_{k:02d}',(1,0,0),angle*fall-.026*wind)
    # Root fans remain planted while the trunk pitches at its base.
    bpy.context.view_layer.update()
    for k in range(8):
        pb=rig.pose.bones[f'rootfan_{k:02d}'];pb.matrix=pb.bone.matrix_local.copy()
    for side,sign in (('L',1),('R',-1)):
        turn('sac_'+side,(1,0,0),-.07*wind+.16*rebound-.04*fall)
        for k in range(3):
            turn(f'mem_{side}_{k}',(1,0,0),-.012*wind+.018*rebound)
            turn(f'chain_{side}_{k}',(1,0,0),-.010*wind+.012*rebound)
    shift('maw',(0,.025*wind,0))
    for pb in rig.pose.bones:
        pb.keyframe_insert('location',frame=frame,group=pb.name)
        pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
        pb.keyframe_insert('scale',frame=frame,group=pb.name)
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports'/f'{name}.fbx'),object_types={'ARMATURE'},use_selection=True,
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype='NULL',path_mode='STRIP',
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(0);rig.animation_data.action=None
for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
obj['hardware_separation']='Rigid welded metal islands; tissue side has no metal weights.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M14_Hardware_TrunkSlam_v11.blend'),compress=True)
report={'complete':True,'metal_islands':islands,'metal_vertices':int(is_metal.sum()),'tissue_vertices_repaired':int(leak.sum()),
        'source_triangles':len(faces),'geometry_removed':0,'source_bones':groups,'slam_seconds':3.2,'slam_contact_seconds':1.2,
        'hardware_export_rows':len(payload),'tested':False,'rendered':False}
(OUT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M14_V11_AUTHORED',len(payload),'vertices;',len(islands),'rigid metal islands',flush=True)
