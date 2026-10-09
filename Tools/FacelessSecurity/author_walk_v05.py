"""Author Walk_B with boot-sole support and same-side arm clearance.

Production bake only; does not render, launch PIE or run acceptance tests.
"""
from pathlib import Path
prefix=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/author_male_v02.py').read_text(encoding='utf-8').split('# Cache only the actually displayed')[0]
prefix=prefix.replace("BASE=ROOT.parent/'V01'",'BASE=ROOT').replace('V02','V05').replace('Authoring/FacelessSecurity_V01.blend','Authoring/FacelessSecurity_V05.blend')
prefix=prefix.replace('rig.animation_data.action=None','rig.animation_data_create();rig.animation_data.action=None')
exec(compile(prefix,'security_walk_fit','exec'))
(ROOT/'Motion').mkdir(parents=True,exist_ok=True)
native,notes=load_cache('walk')

def rotate_quat(pose,bone,q):
    pivot=pose[bone].translation.copy()
    transform=Matrix.Translation(pivot)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)
    for name in children[bone]:pose[name]=transform@pose[name]

def blend_local(a,b,t):
    result={}
    for pb in ordered:
        name=pb.name;parent=pb.parent.name if pb.parent else None
        ma=a[parent].inverted()@a[name] if parent else a[name]
        mb=b[parent].inverted()@b[name] if parent else b[name]
        m=matrix(ma.translation.lerp(mb.translation,t),ma.to_quaternion().slerp(mb.to_quaternion(),t))
        result[name]=result[parent]@m if parent else m
    return result

# Close the source cycle before contact correction, preserving local lengths.
for j in range(7):
    index=len(native)-7+j
    native[index]=blend_local(native[index],native[0],ease(j/6))

sole={};normal={}
for side in ['l','r']:
    o=bpy.data.objects['Security_BootSole_'+side]
    inv=rest['foot_'+side].inverted()
    # The first 80 vertices are the flat underside perimeter of V03 soles.
    sole[side]=[inv@(o.matrix_world@v.co) for v in list(o.data.vertices)[:80]]
    points=np.array([list(v) for v in sole[side]])
    _,_,axes=np.linalg.svd(points-points.mean(0))
    n=Vector(axes[-1]);world_n=rest['foot_'+side].to_quaternion()@n
    if world_n.z<0:n=-n
    normal[side]=n

def sole_points(pose,side):return [pose['foot_'+side]@v for v in sole[side]]

def floor_shift(pose):
    dz=-min(v.z for side in ['l','r'] for v in sole_points(pose,side))
    for m in pose.values():m.translation.z+=dz
    return dz

# Contact envelopes follow each donor foot's lift, smoothed around the loop.
contacts={}
for side in ['l','r']:
    heights=np.array([np.mean([p.z for p in sole_points(row,side)]) for row in native])
    baseline=float(np.percentile(heights,15))
    values=np.array([1-ease((h-baseline-.008)/.045) for h in heights])
    cycle=values[:-1]
    for _ in range(3):cycle=(np.roll(cycle,1)+2*cycle+np.roll(cycle,-1))/4
    contacts[side]=np.r_[cycle,cycle[0]]

def support_leg(pose,side,amount):
    if amount<.001:return
    thigh='thigh_'+side;calf='calf_'+side;foot='foot_'+side
    q=pose[foot].to_quaternion()
    correction=(q@normal[side]).rotation_difference(Vector((0,0,1)))
    flat=correction@q;wanted=q.slerp(flat,float(amount))
    rotate_quat(pose,foot,wanted@q.inverted())
    h=pose[thigh].translation.copy();k=pose[calf].translation.copy();a=pose[foot].translation.copy()
    target=a.copy();target.z=-min((wanted@p).z for p in sole[side])
    target=a.lerp(target,float(amount))
    l1=(k-h).length;l2=(a-k).length
    axis=(target-h).normalized();length=max(abs(l1-l2)+.0001,min((target-h).length,l1+l2-.0005))
    target=h+axis*length
    pole=k-h-axis*(k-h).dot(axis)
    if pole.length<1e-5:pole=Vector((0,-1,0))-axis*axis.dot(Vector((0,-1,0)))
    pole.normalize();along=(l1*l1+length*length-l2*l2)/(2*length)
    bend=math.sqrt(max(0.,l1*l1-along*along));knee=h+axis*along+pole*bend
    rotate_quat(pose,thigh,(k-h).rotation_difference(knee-h))
    current_k=pose[calf].translation.copy();current_a=pose[foot].translation.copy()
    rotate_quat(pose,calf,(current_a-current_k).rotation_difference(target-current_k))
    rotate_quat(pose,foot,wanted@pose[foot].to_quaternion().inverted())

poses=[];shifts=[]
for index,row in enumerate(native):
    pose={n:m.copy() for n,m in row.items()}
    for side,sign in [('l',1),('r',-1)]:
        rotate_branch(pose,'upperarm_'+side,Vector((0,1,0)),math.radians(-sign*3.0))
    # First place the body's lowest outsole on the floor, then solve each
    # supporting leg without stretching its bones or lifting the pelvis.
    dz=floor_shift(pose)
    for side in ['l','r']:support_leg(pose,side,contacts[side][index])
    dz+=floor_shift(pose);shifts.append(dz);poses.append(pose)

velocities=[]
for side in ['l','r']:
    positions=np.array([list(row['foot_'+side].translation) for row in poses])
    velocity=np.gradient(positions,1/FPS,axis=0)
    planted=(contacts[side]>.65)&(velocity[:,1]>.08)
    velocities.extend(velocity[:,1][planted].tolist())
if not velocities:raise RuntimeError('Walk_B has no supporting backward foot travel for playback conversion')
nominal_speed=float(np.median(velocities)*100);walk_rate=26./nominal_speed

scene.render.fps=FPS;scene.render.fps_base=1
for track in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(track)
action=bpy.data.actions.new('Security_MaleV05_walk');rig.animation_data.action=action;previous={}
for index,pose in enumerate(poses,1):
    for pb in ordered:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        desired=pose[parent].inverted()@pose[n] if parent else pose[n]
        basis=local_inverse[n]@desired;location,quat,_=basis.decompose()
        if n in previous and quat.dot(previous[n])<0:quat.negate()
        previous[n]=quat.copy();pb.rotation_mode='QUATERNION';pb.location=location/rig_unit;pb.rotation_quaternion=quat;pb.scale=(1,1,1)
        pb.keyframe_insert(data_path='location',frame=index,group=n)
        pb.keyframe_insert(data_path='rotation_quaternion',frame=index,group=n)
action.use_fake_user=True
scene.frame_start=1;scene.frame_end=len(poses);scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=ROOT/'Motion/A_Security_Male_V05_walk.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
    use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,
    bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
track=rig.animation_data.nla_tracks.new();track.name='MaleV05_walk'
strip=track.strips.new(action.name,1,action);strip.action_slot=action.slots[0];strip.extrapolation='NOTHING';track.mute=True
rig.animation_data.action=None
# Keep the existing production actions available in the editable assembly;
# their UE assets and contact timings are not reimported or changed.
with bpy.data.libraries.load(str(ROOT.parent/'V03/Motion/FacelessSecurity_MaleMotion_V03.blend'),link=False) as (src,dst):
    dst.actions=[name for name in src.actions if name in ['Security_MaleV03_idle','Security_MaleV03_attack']]
for kept in dst.actions:
    if kept:kept.use_fake_user=True
scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Motion/FacelessSecurity_MaleMotion_V05.blend'))
manifest={'revision':'V05 Zombie Walk_B with independent sleeves and sole support','fps':FPS,
    'clips':{'walk':{'file':str(fbx),'action':action.name,'frames':len(poses),'duration':(len(poses)-1)/FPS,
                    'rate_scale':walk_rate,'source_asset':source['clips']['walk']['source']}},
    'source_inputs':source,'native_motion_notes':notes,'walk_source_speed_cm_s':nominal_speed,'walk_rate_scale':walk_rate,
    'controller_speed_denominator_cm_s':26.,'walk_speed_cm_s':78.,
    'grounding':'Actual sole undersides, smoothed stance envelopes, planted-foot flattening and fixed-length two-bone leg support; sole plane at 0 m',
    'mesh_floor_gap_compensation_cm':2.15,'shoulder_clearance_degrees':3.,
    'preserved_ue_clips':['V03 idle','V03 attack'],'game_tested':False,'rendered':False,
    'native_stage_process_exit':1,'native_stage_note':'Pose cache and intermediate raw asset saved; retarget commandlet reported result 0 before an animation-compression shutdown assertion. Final delivery uses the separately baked and imported FBX.'}
(ROOT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('SECURITY_WALK_V05_AUTHORED '+json.dumps(manifest['clips']),flush=True)
