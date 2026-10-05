"""Keep material-cut seams together and fit rigid chains to the falling trunk."""
from pathlib import Path
import bpy, json, struct
import numpy as np
from mathutils import Matrix, kdtree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004');OUT=ROOT/'ProductionV13'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ProductionV12/Authoring/M14_Whirlwind_v12.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['M14_Rig'];obj=bpy.data.objects['M14_SoftDeathMesh'];mesh=obj.data
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
modifiers=[(m,m.show_viewport) for m in obj.modifiers if m.type=='ARMATURE']
for m,_ in modifiers:m.show_viewport=False
d=np.load(ROOT/'ProductionV11/Records/hardware_source.npz');binding=np.load(OUT/'Records/hardware_binding.npz')
p=d['p'].astype(np.float64);faces=d['f'];metal=np.zeros(len(p),bool);metal[np.unique(faces[d['metal']])]=True
owner=binding['owner'];blend=binding['blend'];changed=np.flatnonzero(blend>0)
groups=[g.name for g in obj.vertex_groups]
islands=json.loads((ROOT/'ProductionV11/Records/authoring.json').read_text())['metal_islands']
owner_bone={int(cid):islands[int(cid)]['bone'] for cid in binding['major']}
old_w=np.zeros((len(p),len(groups)),np.float32)
for i,v in enumerate(mesh.vertices):
    for g in v.groups:old_w[i,g.group]=g.weight
new_w=old_w[changed]*(1-blend[changed,None])
for cid,bone in owner_bone.items():new_w[owner[changed]==cid,groups.index(bone)]+=blend[changed[owner[changed]==cid]]
bone_ids=np.argsort(new_w,axis=1)[:,-4:][:,::-1]
weights=np.take_along_axis(new_w,bone_ids,axis=1);weights/=np.maximum(weights.sum(1,keepdims=True),1.e-8)
# Matched source points (including metal/tissue duplicates) share one result.
weld=np.load(ROOT/'ProductionV11/Records/hardware_components.npz')['weld']
_,representative,inverse=np.unique(weld[changed],return_index=True,return_inverse=True)
bone_ids=bone_ids[representative][inverse];weights=weights[representative][inverse]
for g in obj.vertex_groups:g.remove(changed.tolist())
for slot in range(4):
    active=np.flatnonzero(weights[:,slot]>0);keys=bone_ids[active,slot]*65536+np.rint(weights[active,slot]*65535).astype(np.int64)
    order=np.argsort(keys);active=active[order];keys=keys[order]
    values,starts=np.unique(keys,return_index=True);ends=np.r_[starts[1:],len(keys)]
    for value,start,end in zip(values,starts,ends):
        obj.vertex_groups[int(value//65536)].add(changed[active[start:end]].tolist(),float(value%65536)/65535,'REPLACE')

def rigid_fit(source,destination):
    center=source.mean(0);dest=destination.mean(0)
    a,_,bt=np.linalg.svd((source-center).T@(destination-dest));rotation=a@bt
    if np.linalg.det(rotation)<0:a[:,-1]*=-1;rotation=a@bt
    matrix=np.eye(4);matrix[:3,:3]=rotation.T;matrix[:3,3]=dest-center@rotation
    return matrix

# Reconstruct the shared tissue collapse field from the V06 source; fitting
# fragmented V11 morph islands again would preserve their separated trajectories.
# The source coordinates are evaluated by the same production field below,
# avoiding a second copy of the dense source mesh in this authoring scene.
def smooth(v):v=np.clip(v,0,1);return v*v*(3-2*v)
x,y,z=p.T
final=np.column_stack((x*(1.32+.10*np.sin(z*1.7))+.20*np.sin(z*1.45),y*1.20+.65*z+.12*np.sin(z*2),.014+.080*z+.025*np.sin(z*3)**2))
mouth=np.array(rig.data.bones['maw'].head_local);delta=p-mouth
r=np.sqrt((delta[:,0]/.30)**2+(delta[:,1]/.22)**2+(delta[:,2]/.28)**2);w=1-smooth((r-.72)/.78)
angle=np.radians(-76);co,si=np.cos(angle),np.sin(angle);rotation=np.array([[1,0,0],[0,co,-si],[0,si,co]])
mouth_at=np.array([.20*np.sin(mouth[2]*1.45),mouth[1]*1.2+.65*mouth[2]+.12*np.sin(mouth[2]*2),.23])
final=final*(1-w[:,None])+(delta@rotation.T+mouth_at)*w[:,None]
delta=p-[0,0,2.03];r=np.sqrt((delta[:,0]/.42)**2+(delta[:,1]/.37)**2+(delta[:,2]/.15)**2);w=1-smooth((r-.88)/.72)
band_at=np.array([.20*np.sin(2.03*1.45),.65*2.03+.12*np.sin(2.03*2),.18])
final=final*(1-w[:,None])+(delta+band_at)*w[:,None]
for side in ('L','R'):
    sac=np.array(rig.data.bones['sac_'+side].head_local);sac[2]-=.18;delta=p-sac
    final[:,2]+=.11*np.exp(-2*((delta[:,0]/.23)**2+(delta[:,1]/.21)**2+(delta[:,2]/.30)**2))
final[:,2]=np.maximum(.012,final[:,2])
shape_names=['M14_DeathSag','M14_DeathFold','M14_DeathSpread'];shapes=[]
for j,(name,time) in enumerate(zip(shape_names,(.75,1.6,2.7))):
    delay=.07+.16*np.clip(z,0,3)+.08*smooth(x+.5)
    phase=np.ones(len(p)) if j==2 else smooth((time-delay)/(1.55+.12*np.clip(z,0,3)))
    target=p+(final-p)*phase[:,None]
    if j<2:
        sway=np.sin(np.pi*phase)*.13;target[:,0]+=sway*np.sin(z*1.8);target[:,1]-=sway*.35
    q=np.empty(len(p)*3,np.float32);mesh.shape_keys.key_blocks[name].data.foreach_get('co',q);q=q.reshape(-1,3)
    for cid in owner_bone:
        solid=np.flatnonzero((owner==cid)&(blend>=.999999));affected=np.flatnonzero((owner==cid)&(blend>0))
        transform=rigid_fit(p[solid],target[solid])
        if j==2:
            landed=p[solid]@transform[:3,:3].T+transform[:3,3]
            transform[2,3]+=max(0.,.012-float(landed[:,2].min()))
        rigid=p[affected]@transform[:3,:3].T+transform[:3,3]
        q[affected]=target[affected]*(1-blend[affected,None])+rigid*blend[affected,None]
    q[changed]=q[changed][representative][inverse]
    mesh.shape_keys.key_blocks[name].data.foreach_set('co',q.ravel());mesh.shape_keys.key_blocks[name].value=0
    shapes.append(q)
payload=np.zeros((len(changed),21),np.float32);payload[:,:3]=p[changed];payload[:,3]=metal[changed]
payload[:,4:8]=bone_ids;payload[:,8:12]=weights
for j,q in enumerate(shapes):payload[:,12+3*j:15+3*j]=q[changed]-p[changed]
with (OUT/'Exports/hardware_skin.bin').open('wb') as stream:
    stream.write(struct.pack('<i',len(payload)));stream.write(payload.astype('<f4').tobytes())
(OUT/'Exports/hardware_bones.json').write_text(json.dumps(groups),encoding='utf8')

# Fit each existing hardware bone to nearby unmodified tissue trajectory.
# This bakes all motion; no runtime per-vertex fitting or extra physics bodies.
metal_bones=sorted(set(owner_bone.values()),key=lambda name:len(rig.data.bones[name].parent_recursive))
metal_indices=[groups.index(name) for name in groups if name.startswith('chain_') or name=='restraint']
clean=np.flatnonzero((blend==0)&(old_w[:,metal_indices].sum(1)<.001))
tree=kdtree.KDTree(len(clean))
for i in clean:tree.insert(p[i],int(i))
tree.balance();controls={}
for bone in metal_bones:
    ids=np.flatnonzero(np.isin(owner,[cid for cid,b in owner_bone.items() if b==bone])&(blend>=.999999))
    sample=ids[np.linspace(0,len(ids)-1,min(256,len(ids))).astype(int)]
    nearest=np.array([tree.find(p[i])[1] for i in sample]);controls[bone]=(p[sample],old_w[nearest])
source=bpy.data.actions['A_M14_TrunkSlam_v11'];action=bpy.data.actions.new('A_M14_TrunkSlam_v13');action.use_fake_user=True
scene.render.fps=30;scene.frame_start=0;scene.frame_end=96
rest_inverse={b.name:b.matrix_local.inverted() for b in rig.data.bones}
for frame in range(97):
    rig.animation_data.action=source;scene.frame_set(frame);bpy.context.view_layer.update()
    skin=np.array([rig.pose.bones[name].matrix@rest_inverse[name] for name in groups])
    desired={}
    for bone,(points,anchors) in controls.items():
        goal=np.zeros_like(points)
        for k in np.flatnonzero(anchors.sum(0)>0):
            goal+=(points@skin[k,:3,:3].T+skin[k,:3,3])*anchors[:,k,None]
        desired[bone]=rigid_fit(points,goal)
    for bone in metal_bones:
        rig.pose.bones[bone].matrix=Matrix(desired[bone].tolist())@rig.data.bones[bone].matrix_local
        bpy.context.view_layer.update()
    channels={pb.name:(pb.location.copy(),pb.rotation_quaternion.copy()) for pb in rig.pose.bones}
    rig.animation_data.action=action
    for pb in rig.pose.bones:
        pb.location,pb.rotation_quaternion=channels[pb.name]
        pb.scale=(1,1,1)
        pb.keyframe_insert('location',frame=frame,group=pb.name);pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name);pb.keyframe_insert('scale',frame=frame,group=pb.name)
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/A_M14_TrunkSlam_v13.fbx'),object_types={'ARMATURE'},use_selection=True,
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,
    use_armature_deform_only=True,armature_nodetype='NULL',path_mode='STRIP',bake_anim=True,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
for m,value in modifiers:m.show_viewport=value
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M14_HardwareSeams_Spit_v13.blend'),compress=True)
report={'complete':True,'source':'ProductionV12','changed_vertices':len(changed),'rigid_regions':len(owner_bone),
    'coincident_seams_unified':True,'transition_width_m':.06,'slam_hardware_bones':metal_bones,
    'source_triangles':len(faces),'geometry_removed':0,'slam_seconds':3.2,'slam_contact_seconds':1.2,'tested':False,'rendered':False}
(OUT/'Records/authoring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('M14_V13_SOURCE_SAVED',len(changed),flush=True)
