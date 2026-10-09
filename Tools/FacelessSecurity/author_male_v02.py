"""Fit and time the existing male actions on the intact clothed security rig.

Authoring only: no scene rendering, preview playback or runtime test.
"""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V02')
BASE=ROOT.parent/'V01';FPS=60
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/FacelessSecurity_V01.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['root']
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
scene.frame_set(0)
raw=list(rig['source_world_matrix']);rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
ordered=sorted(rig.pose.bones,key=lambda p:len(p.bone.parent_recursive))
# Work in metric, unit-scale bone frames; the imported rig object carries
# FBX centimetre scaling. Convert translation keys back only when baking.
rig_unit=float(rig.matrix_world.to_scale().x)
rest={}
for b in rig.data.bones:
    m=rig.matrix_world@b.matrix_local
    rest[b.name]=Matrix.LocRotScale(m.translation,m.to_quaternion(),Vector((1,1,1)))
local={p.name:rest[p.parent.name].inverted()@rest[p.name] if p.parent else rest[p.name] for p in ordered}
local_inverse={n:m.inverted() for n,m in local.items()}
source=json.loads((ROOT/'native_retarget.json').read_text())
def matrix(p,q):return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def ease(t):
    t=max(0.,min(1.,float(t)));return t*t*t*(10+t*(-15+6*t))
def frame(pose):
    across=(pose['upperarm_l'].translation-pose['upperarm_r'].translation).normalized()
    up=(pose['head'].translation-pose['pelvis'].translation).normalized();up=(up-across*up.dot(across)).normalized()
    return Matrix((across,up.cross(across),up)).transposed()
def load_cache(role):
    src=json.loads(Path(source['clips'][role]['pose_cache']).read_text())
    reflect=Matrix(((1,0,0),(0,-1,0),(0,0,1)))
    def convert(row):
        result={}
        for n,v in row.items():
            x,y,z,w=v['rotation_xyzw'];q=(reflect@Quaternion((w,x,y,z)).to_matrix()@reflect).to_quaternion()
            result[n]=matrix((reflect@Vector(v['translation_cm']))*.01,q)
        return result
    ref=convert(src['reference']);reg=frame(rest)@frame(ref).transposed();qreg=reg.to_quaternion();poses=[]
    for row in src['frames']:
        raw=convert(row);target={}
        for pb in ordered:
            n=pb.name
            q=qreg@raw[n].to_quaternion()@ref[n].to_quaternion().inverted()@qreg.inverted()@rest[n].to_quaternion()
            p=target[pb.parent.name]@local[n].translation if pb.parent else rest[n].translation.copy()
            if n=='pelvis':p=rest[n].translation+reg@(raw[n].translation-ref[n].translation)
            target[n]=matrix(p,q)
        poses.append(target)
    start=poses[0]['pelvis'].translation;drift=poses[-1]['pelvis'].translation-start
    for i,pose in enumerate(poses):
        offset=Vector((-start.x-drift.x*i/(len(poses)-1),-start.y-drift.y*i/(len(poses)-1),0))
        for m in pose.values():m.translation+=offset
    return poses,{'source_pelvis_net_translation_m':list(drift),'source_frames':len(poses)}
def sample(poses,time):
    f=np.clip(time*FPS,0,len(poses)-1);a=int(f);b=min(a+1,len(poses)-1);t=f-a
    return {n:matrix(poses[a][n].translation.lerp(poses[b][n].translation,float(t)),poses[a][n].to_quaternion().slerp(poses[b][n].to_quaternion(),float(t))) for n in rest}
children={n:[p.name for p in ordered if p.name==n or n in [b.name for b in p.bone.parent_recursive]] for n in rest}
def rotate_branch(pose,bone,axis,angle):
    pivot=pose[bone].translation;rot=Quaternion(axis,angle);transform=Matrix.Translation(pivot)@rot.to_matrix().to_4x4()@Matrix.Translation(-pivot)
    for n in children[bone]:pose[n]=transform@pose[n]
def tailoring(pose,role):
    # Modest forward readiness and whole-arm clearance preserve the donor's
    # shoulder/elbow/wrist relationships on the broad clothed body.
    if role!='attack':rotate_branch(pose,'spine_03',Vector((1,0,0)),math.radians(2.4))
    for side,sign in [('l',1),('r',-1)]:
        rotate_branch(pose,'upperarm_'+side,Vector((0,1,0)),math.radians(-sign*(3.5 if role=='attack' else 5.0)))
    return pose
# Cache only the actually displayed boot/sole support vertices for offline
# grounding. An arm, trouser flap or hidden complete body cannot set the floor.
support={}
for o in scene.objects:
    if o.type!='MESH' or not o.name.startswith(('Security_Boot_','Security_BootSole_')):continue
    names={g.index:g.name for g in o.vertex_groups if g.name in rest}
    for v in o.data.vertices:
        ws={names[g.group]:g.weight for g in v.groups if g.group in names}
        if sum(w for n,w in ws.items() if n.startswith(('foot_','ball_')))<.6:continue
        p=o.matrix_world@v.co
        for n,w in ws.items():
            support.setdefault(n,[]).append((p,w,len(support.get('__vertices',[]))))
        support.setdefault('__vertices',[]).append(p)
count=len(support.pop('__vertices'));inputs={}
for n,rows in support.items():
    a=np.zeros((count,4));inv=rest[n].inverted()
    for p,w,i in rows:
        q=inv@p;a[i]=np.array([*q,1])*w
    inputs[n]=a
def ground(pose):
    heights=sum(a@np.array(pose[n])[2,:] for n,a in inputs.items())
    dz=.002-float(np.min(heights))
    for m in pose.values():m.translation.z+=dz
    return dz
def local_blend(pose,idle,weights):
    result={}
    for pb in ordered:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        a=idle[parent].inverted()@idle[n] if parent else idle[n]
        b=pose[parent].inverted()@pose[n] if parent else pose[n]
        t=weights(n);m=matrix(a.translation.lerp(b.translation,t),a.to_quaternion().slerp(b.to_quaternion(),t))
        result[n]=result[parent]@m if parent else m
    return result
native={};native_notes={}
for role in ['idle','walk','attack']:native[role],native_notes[role]=load_cache(role)
# In-place male stride speed is derived from each planted foot's backward
# travel. The existing Nurse controller sets rate = velocity / 26 cm/s.
walk=native['walk'];velocities=[]
for side in ['l','r']:
    p=np.array([row['foot_'+side].translation[:] for row in walk]);v=np.gradient(p,1/FPS,axis=0)
    low=p[:,2]<np.percentile(p[:,2],40)+.004
    candidates=v[:,1][low & (v[:,1]>.08)]
    velocities.extend(candidates.tolist())
if not velocities:raise RuntimeError('Male walk has no usable planted-foot travel for playback conversion')
nominal_speed=float(np.median(velocities)*100)
walk_rate=26.0/nominal_speed
idle_poses=[]
for p in native['idle']:
    pose=tailoring({n:m.copy() for n,m in p.items()},'idle');ground(pose);idle_poses.append(pose)
walk_poses=[]
for p in native['walk']:
    pose=tailoring({n:m.copy() for n,m in p.items()},'walk');ground(pose);walk_poses.append(pose)
def close_loop(poses,seconds):
    number=min(round(seconds*FPS),len(poses)//4)
    for j in range(number+1):
        i=len(poses)-number-1+j;amount=ease(j/number)
        poses[i]=local_blend(poses[i],poses[0],lambda n:1-amount);ground(poses[i])
close_loop(idle_poses,.30);close_loop(walk_poses,.13)
# Guard attack: deliberate wind-up, brief explosive downward sweep, then
# controlled recovery to the new male idle. Preserve the whole-body donor.
out_times=[0.,.18,.55,.68,.86,1.28,2.30]
source_times=[0.,.12,.40,.63,.80,1.13,2.0]
attack_poses=[];idle0=idle_poses[0]
for i in range(round(2.30*FPS)+1):
    t=i/FPS;src=float(np.interp(t,out_times,source_times));pose=tailoring(sample(native['attack'],src),'attack')
    def weight(n):
        delay=.12 if n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')) else .07 if n.startswith(('upperarm_','lowerarm_','clavicle_')) else .03 if n.startswith(('neck_','head')) else 0.
        return ease(t/.18)*(1-ease((t-1.18-delay)/(2.30-1.18-delay)))
    pose=local_blend(pose,idle0,weight);ground(pose);attack_poses.append(pose)
contact_start=float(np.interp(.47,source_times,out_times));contact_end=float(np.interp(.73,source_times,out_times))
scene.render.fps=FPS;scene.render.fps_base=1
for tr in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(tr)
manifest={'revision':'V02 male locomotion and weighted strike','fps':FPS,'clips':{},'source_inputs':source,
    'fit':'2.4 degree ready lean for idle/walk; whole-arm shoulder clearance; actual boot sole grounding; source bone lengths retained',
    'walk_source_speed_cm_s':nominal_speed,'walk_rate_scale':walk_rate,'controller_speed_denominator_cm_s':26.,
    'walk_speed_cm_s':78.,'contact_time':contact_start,'contact_end':contact_end,'recovery_time':.38,
    'geometry_modified':False,'weights_modified':False,'rendered':False,'tested':False,'native_stage_process_exit':1,
    'native_stage_note':'All raw clips and caches saved; native retarget commandlet hit animation compression task assertion during shutdown. Final FBX animation import is a separate stage.',
    'native_motion_notes':native_notes}
for role,poses in [('idle',idle_poses),('walk',walk_poses),('attack',attack_poses)]:
    action=bpy.data.actions.new('Security_MaleV02_'+role);rig.animation_data.action=action
    prev_quats={}
    for frame_index,pose in enumerate(poses,1):
        for pb in ordered:
            n=pb.name;parent=pb.parent.name if pb.parent else None
            desired=pose[parent].inverted()@pose[n] if parent else pose[n]
            basis=local_inverse[n]@desired;pos,quat,_=basis.decompose()
            if n in prev_quats and quat.dot(prev_quats[n])<0:quat.negate()
            prev_quats[n]=quat.copy();pb.rotation_mode='QUATERNION';pb.location=pos/rig_unit;pb.rotation_quaternion=quat;pb.scale=(1,1,1)
            pb.keyframe_insert(data_path='location',frame=frame_index,group=n);pb.keyframe_insert(data_path='rotation_quaternion',frame=frame_index,group=n)
    action.use_fake_user=True
    scene.frame_start=1;scene.frame_end=len(poses);scene.frame_set(0)
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    fbx=ROOT/'Motion'/('A_Security_Male_V02_'+role+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
        use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,
        bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
    track=rig.animation_data.nla_tracks.new();track.name='MaleV02_'+role
    strip=track.strips.new(action.name,1,action);strip.action_slot=action.slots[0];strip.extrapolation='NOTHING';track.mute=True
    manifest['clips'][role]={'file':str(fbx),'action':action.name,'frames':len(poses),'duration':(len(poses)-1)/FPS,
        'rate_scale':walk_rate if role=='walk' else 1.,'source_asset':source['clips'][role]['source']}
    print('SECURITY_MALE_MOTION_SAVED '+role+' '+str(fbx),flush=True)
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
scene.frame_start=1;scene.frame_end=len(idle_poses)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Motion/FacelessSecurity_MaleMotion_V02.blend'))
(ROOT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('SECURITY_MALE_V02_AUTHORED '+json.dumps({'walk_nominal_cm_s':nominal_speed,'walk_rate_scale':walk_rate,'contact':[contact_start,contact_end],'clips':manifest['clips']}),flush=True)
