"""Align guard recovery, idle and locomotion at one supported ready pose."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/author_male_v02.py').read_text(encoding='utf-8')
prefix=src.split('# Cache only the actually displayed')[0]
prefix=prefix.replace("BASE=ROOT.parent/'V01'",'BASE=ROOT').replace('V02','V06').replace('Authoring/FacelessSecurity_V01.blend','Authoring/FacelessSecurity_V06.blend')
prefix=prefix.replace('rig.animation_data.action=None','rig.animation_data_create();rig.animation_data.action=None')
prefix=prefix.replace("ROOT/'native_retarget.json'","ROOT.parent/'V03/native_retarget.json'")
exec(compile(prefix,'security_recovery_helpers','exec'))

def copy_pose(p):return {n:m.copy() for n,m in p.items()}

def read_action(path,name,count):
    with bpy.data.libraries.load(str(path),link=False) as (data_from,data_to):data_to.actions=[name]
    action=data_to.actions[0];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    poses=[]
    for i in range(1,count+1):
        scene.frame_set(i);row={}
        for pb in ordered:
            m=rig.matrix_world@pb.matrix;row[pb.name]=matrix(m.translation,m.to_quaternion())
        poses.append(row)
    rig.animation_data.action=None;return poses

walk=read_action(ROOT.parent/'V05/Motion/FacelessSecurity_MaleMotion_V05.blend','Security_MaleV05_walk',239)
old_idle=read_action(ROOT.parent/'V03/Motion/FacelessSecurity_MaleMotion_V03.blend','Security_MaleV03_idle',239)
old_attack=read_action(ROOT.parent/'V03/Motion/FacelessSecurity_MaleMotion_V03.blend','Security_MaleV03_attack',139)
native_attack,attack_notes=load_cache('attack')
sole={}
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for side in ['l','r']:
    o=bpy.data.objects['Security_BootSole_'+side];inv=rest['foot_'+side].inverted()
    sole[side]=[inv@(o.matrix_world@v.co) for v in list(o.data.vertices)[:80]]

def ground(pose):
    dz=-min((pose['foot_'+side]@v).z for side in ['l','r'] for v in sole[side])
    for m in pose.values():m.translation.z+=dz

def local_blend(a,b,weight):
    result={}
    for pb in ordered:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        ma=a[parent].inverted()@a[n] if parent else a[n]
        mb=b[parent].inverted()@b[n] if parent else b[n];t=float(weight(n))
        m=matrix(ma.translation.lerp(mb.translation,t),ma.to_quaternion().slerp(mb.to_quaternion(),t))
        result[n]=result[parent]@m if parent else m
    return result

# Rephase the same Walk_B cycle to its most supported double-foot stance.
# This supplies a ready pose without inventing an unrelated idle posture.
def support_score(pose):
    left=[pose['foot_l']@v for v in sole['l']];right=[pose['foot_r']@v for v in sole['r']]
    height=max(np.mean([p.z for p in left]),np.mean([p.z for p in right]))
    a=pose['foot_l'].translation;b=pose['foot_r'].translation
    return float(8*height+.20*abs(a.y-b.y)+.5*max(0.,.24-abs(a.x-b.x)))
phase=min(range(len(walk)-1),key=lambda i:support_score(walk[i]))
cycle=walk[:-1];walk_poses=cycle[phase:]+cycle[:phase]+[copy_pose(cycle[phase])]
ready=copy_pose(walk_poses[0]);ground(ready)
for pose in walk_poses:ground(pose)

# Keep the donor idle's small upper-body movement around the ready stance.
# The legs retain the supported Walk_B stance; the first/last poses coincide
# with the recovery end and new walk start.
idle_poses=[]
for old in old_idle:
    result={}
    for pb in ordered:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        base=ready[parent].inverted()@ready[n] if parent else ready[n]
        first=old_idle[0][parent].inverted()@old_idle[0][n] if parent else old_idle[0][n]
        current=old[parent].inverted()@old[n] if parent else old[n]
        amount=.28 if n.startswith(('spine_','neck_','head')) else .20 if n.startswith(('clavicle_','upperarm_','lowerarm_','hand_')) else .10 if n.startswith(('thumb_','index_','middle_','ring_','pinky_')) else 0.
        delta=first.to_quaternion().inverted()@current.to_quaternion()
        q=base.to_quaternion()@Quaternion().slerp(delta,amount)
        m=matrix(base.translation,q);result[n]=result[parent]@m if parent else m
    ground(result);idle_poses.append(result)
idle_poses[0]=copy_pose(ready);idle_poses[-1]=copy_pose(ready)

old_manifest=json.loads((ROOT.parent/'V03/motion_manifest.json').read_text(encoding='utf-8'))
walk_manifest=json.loads((ROOT.parent/'V05/motion_manifest.json').read_text(encoding='utf-8'))
duration=154/FPS;recovery_time=2.30+old_manifest['recovery_time']-duration
source_at_join=float(np.interp(1.10,[0.,.18,.55,.68,.86,1.28,2.30],[0.,.12,.40,.63,.80,1.13,2.0]))
attack_poses=[]
for i in range(155):
    t=i/FPS
    if t<=1.10:
        pose=sample(old_attack,t)
        if t<.20:pose=local_blend(ready,pose,lambda n:ease(t/.20))
    else:
        source_time=float(np.interp(t,[1.10,1.80,duration],[source_at_join,1.57,2.0]))
        pose=sample(native_attack,source_time)
        for side,sign in [('l',1),('r',-1)]:
            rotate_branch(pose,'upperarm_'+side,Vector((0,1,0)),math.radians(-sign*4.5))
        ground(pose)
        def recovery(n):
            # Each complete arm uses one curve; wrists/fingers cannot lag
            # behind the elbow and create a final whip or bend reversal.
            if n.startswith(('clavicle_','upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_')):
                start,end=(1.20,2.48) if n.endswith('_l') else (1.24,2.52)
            elif n.startswith(('spine_','neck_','head')):start,end=1.12,2.35
            else:start,end=1.10,2.46
            return ease((t-start)/(end-start))
        pose=local_blend(pose,ready,recovery)
    ground(pose);attack_poses.append(pose)
attack_poses[-1]=copy_pose(ready)

scene.render.fps=FPS;scene.render.fps_base=1
for track in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(track)
manifest={'revision':'V06 connected shoulders and matched recovery/idle/walk stance','fps':FPS,'clips':{},
    'walk_source_speed_cm_s':walk_manifest['walk_source_speed_cm_s'],'walk_rate_scale':walk_manifest['walk_rate_scale'],
    'walk_speed_cm_s':78.,'contact_time':old_manifest['contact_time'],'contact_end':old_manifest['contact_end'],
    'recovery_time':recovery_time,'attack_cycle_seconds':duration+recovery_time,'walk_phase_source_frame':phase+1,
    'recovery':'Preserve strike after 0.20 through 1.10 s; native Attack_D return with complete-arm curves; finish at the same ready pose as idle and walk',
    'idle':'Idle_A upper-body deltas at 20-28 percent around supported Walk_B ready pose; legs fixed in that stance',
    'geometry_modified':True,'weights_modified':True,'game_tested':False,'rendered':False}
source_names={'idle':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Idle_A',
              'walk':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Walk_B',
              'attack':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Attack_D'}
for role,poses in [('idle',idle_poses),('walk',walk_poses),('attack',attack_poses)]:
    action=bpy.data.actions.new('Security_MaleV06_'+role);rig.animation_data.action=action;previous={}
    for frame_index,pose in enumerate(poses,1):
        for pb in ordered:
            n=pb.name;parent=pb.parent.name if pb.parent else None
            desired=pose[parent].inverted()@pose[n] if parent else pose[n]
            basis=local_inverse[n]@desired;pos,quat,_=basis.decompose()
            if n in previous and quat.dot(previous[n])<0:quat.negate()
            previous[n]=quat.copy();pb.rotation_mode='QUATERNION';pb.location=pos/rig_unit;pb.rotation_quaternion=quat;pb.scale=(1,1,1)
            pb.keyframe_insert(data_path='location',frame=frame_index,group=n);pb.keyframe_insert(data_path='rotation_quaternion',frame=frame_index,group=n)
    action.use_fake_user=True;scene.frame_start=1;scene.frame_end=len(poses);scene.frame_set(0)
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    fbx=ROOT/'Motion'/('A_Security_Male_V06_'+role+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
        use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,
        bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
    track=rig.animation_data.nla_tracks.new();track.name='MaleV06_'+role
    strip=track.strips.new(action.name,1,action);strip.action_slot=action.slots[0];strip.extrapolation='NOTHING';track.mute=True
    manifest['clips'][role]={'file':str(fbx),'action':action.name,'frames':len(poses),'duration':(len(poses)-1)/FPS,
        'rate_scale':manifest['walk_rate_scale'] if role=='walk' else 1.,'source_asset':source_names[role]}
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Motion/FacelessSecurity_MaleMotion_V06.blend'))
(ROOT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('SECURITY_RECOVERY_V06_AUTHORED '+json.dumps(manifest),flush=True)
