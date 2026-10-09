"""Bake a velocity-continuous whole-body recovery; preserve the existing strike."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/author_male_v02.py').read_text(encoding='utf-8')
prefix=src.split('# Cache only the actually displayed')[0]
prefix=prefix.replace("BASE=ROOT.parent/'V01'",'BASE=ROOT').replace('V02','V10').replace('Authoring/FacelessSecurity_V01.blend','Authoring/FacelessSecurity_V10.blend')
prefix=prefix.replace('rig.animation_data.action=None','rig.animation_data_create();rig.animation_data.action=None')
prefix=prefix.replace("ROOT/'native_retarget.json'","ROOT.parent/'V03/native_retarget.json'")
exec(compile(prefix,'security_v10_motion_helpers','exec'))
old_manifest=json.loads((ROOT.parent/'V06/motion_manifest.json').read_text(encoding='utf-8'))

def copy_pose(p):return {n:m.copy() for n,m in p.items()}
def read_action(name,count):
    with bpy.data.libraries.load(str(ROOT.parent/'V06/Motion/FacelessSecurity_MaleMotion_V06.blend'),link=False) as (a,b):b.actions=[name]
    action=b.actions[0];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];poses=[]
    for i in range(1,count+1):
        scene.frame_set(i);poses.append({pb.name:matrix((rig.matrix_world@pb.matrix).translation,(rig.matrix_world@pb.matrix).to_quaternion()) for pb in ordered})
    rig.animation_data.action=None;return poses
old=read_action('Security_MaleV06_attack',155);ready=read_action('Security_MaleV06_idle',1)[0]
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
sole={side:[rest['foot_'+side].inverted()@(bpy.data.objects['Security_BootSole_'+side].matrix_world@v.co) for v in list(bpy.data.objects['Security_BootSole_'+side].data.vertices)[:80]] for side in ['l','r']}
def ground(pose):
    dz=-min((pose['foot_'+side]@v).z for side in ['l','r'] for v in sole[side])
    for m in pose.values():m.translation.z+=dz

JOIN=66;join_time=JOIN/FPS;frames=161;duration=(frames-1)/FPS
def local_pose(pose):return {pb.name:(pose[pb.parent.name].inverted()@pose[pb.name] if pb.parent else pose[pb.name]) for pb in ordered}
start=local_pose(old[JOIN]);previous=local_pose(old[JOIN-3]);previous2=local_pose(old[JOIN-6]);target=local_pose(ready);dt=3/FPS
def rotation_vector(q):
    q=q.normalized()
    if q.w<0:q.negate()
    axis,angle=q.to_axis_angle();return axis*angle if angle>1e-7 else Vector((0,0,0))
def exp_rotation(v):return Quaternion(v.normalized(),v.length) if v.length>1e-8 else Quaternion()
def finish_time(name):
    if name.startswith(('clavicle_','upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_','wrist_')):
        return 2.62 if name.endswith('_l') else 2.65
    if name.startswith(('neck_','head')):return 2.56
    if name.startswith('spine_'):return 2.49
    return 2.43

curves={}
for pb in ordered:
    n=pb.name;a=start[n];q=a.to_quaternion();r1=rotation_vector(q.inverted()@previous[n].to_quaternion());r2=rotation_vector(q.inverted()@previous2[n].to_quaternion())
    velocity=(-4*r1+r2)/(2*dt);acceleration=(r2-2*r1)/(dt*dt)
    p=a.translation;v=(3*p-4*previous[n].translation+previous2[n].translation)/(2*dt)
    acc=(p-2*previous[n].translation+previous2[n].translation)/(dt*dt)
    curves[n]=(q,rotation_vector(q.inverted()@target[n].to_quaternion()),velocity,acceleration,p,target[n].translation-p,v,acc)

def continue_curve(delta,velocity,acceleration,u,seconds):
    # Quintic Hermite constraints retain incoming motion, and end at the
    # ready pose with zero velocity and acceleration. A short continuation
    # window absorbs the strike's momentum instead of adding a long overshoot.
    h01=10*u**3-15*u**4+6*u**5
    tau=.20;elapsed=u*seconds
    decay=(1-ease(elapsed/tau)) if elapsed<tau else 0.
    return delta*h01+(velocity*elapsed+acceleration*(.5*elapsed*elapsed))*decay

poses=[]
for i in range(frames):
    t=i/FPS
    if i<=JOIN:poses.append(copy_pose(old[i]));continue
    pose={}
    for pb in ordered:
        n=pb.name;q,delta,velocity,acceleration,p,dp,v,acc=curves[n];seconds=finish_time(n)-join_time;u=max(0.,min(1.,(t-join_time)/seconds))
        rot=q@exp_rotation(continue_curve(delta,velocity,acceleration,u,seconds))
        pos=p+continue_curve(dp,v,acc,u,seconds)
        m=matrix(pos,rot);pose[n]=pose[pb.parent.name]@m if pb.parent else m
    ground(pose);poses.append(pose)
poses[-1]=copy_pose(ready)
scene.render.fps=FPS;scene.render.fps_base=1
for tr in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(tr)
action=bpy.data.actions.new('Security_MaleV10_attack');rig.animation_data.action=action;last={}
for frame_index,pose in enumerate(poses,1):
    for pb in ordered:
        n=pb.name;desired=pose[pb.parent.name].inverted()@pose[n] if pb.parent else pose[n];basis=local_inverse[n]@desired;pos,q,_=basis.decompose()
        if n in last and q.dot(last[n])<0:q.negate()
        last[n]=q.copy();pb.rotation_mode='QUATERNION';pb.location=pos/rig_unit;pb.rotation_quaternion=q;pb.scale=(1,1,1)
        pb.keyframe_insert(data_path='location',frame=frame_index,group=n);pb.keyframe_insert(data_path='rotation_quaternion',frame=frame_index,group=n)
action.use_fake_user=True;scene.frame_start=1;scene.frame_end=frames;scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=ROOT/'Motion/A_Security_Male_V10_attack.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
    use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Motion/FacelessSecurity_Recovery_V10.blend'))
manifest={'revision':'V10 whole-body continuous recovery','fps':FPS,'clips':{'attack':{'file':str(fbx),'action':action.name,'frames':frames,'duration':duration,'rate_scale':1.,'source_asset':old_manifest['clips']['attack']['source_asset']}},
 'preserved_attack_seconds':[0,join_time],'contact_time':old_manifest['contact_time'],'contact_end':old_manifest['contact_end'],
 'attack_cycle_seconds':old_manifest['attack_cycle_seconds'],'recovery_time':old_manifest['attack_cycle_seconds']-duration,
 'recovery':'Continue incoming full-body motion for 0.20 s, settle pelvis/spine before whole arms, retain local bone lengths, finish at existing V06 ready pose',
 'idle_and_walk':'Existing V06 assets unchanged','game_tested':False,'rendered':False}
(ROOT/'motion_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('SECURITY_V10_RECOVERY_AUTHORED '+json.dumps(manifest),flush=True)
