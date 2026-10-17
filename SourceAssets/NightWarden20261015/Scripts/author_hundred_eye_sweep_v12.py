"""Reuse Hundred-Eyed Slag's full Rampage biped sweep and phase schedule.
Keep native anatomical joint rotations: no independent shoulder/elbow/wrist
optimizer, hand target or rigid cloth avoidance envelope. V10 mesh is unchanged.
"""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
BASE=Path(__file__).resolve().parents[1];P=BASE/'V12HundredEyeSweep';FPS=60;DURATION=1.4;COUNT=85
for folder in ['Motion','Records','Authoring']:(P/folder).mkdir(parents=True,exist_ok=True)
data=json.loads((P/'Motion/native_attack.json').read_text(encoding='utf-8'))
idle_data=json.loads((BASE/'V08AIMovement/Motion/idle_keys.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V14BareBodyHand/Authoring/NightWarden_BareBody_HandRepair_V14.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=bpy.data.objects['NW14_CompleteBody_HandRepair']
rig.data.pose_position='POSE'
def mat(v):return Matrix.LocRotScale(Vector(v['p']),Quaternion((v['q'][3],*v['q'][:3])),Vector(v['s']))
names=list(data['reference']);parent={n:p if p in names else None for n,p in data['parents'].items()}
root=next(n for n in names if parent[n] is None);ref={n:mat(v) for n,v in data['reference'].items()};inv_ref={n:m.inverted() for n,m in ref.items()}
local_ref={n:mat(v) for n,v in data['reference_local'].items()}
def depth(n):return depth(parent[n])+1 if parent[n] else 0
ordered=sorted(names,key=depth)
def ancestors(n):
 out=[]
 while parent[n]:n=parent[n];out.append(n)
 return out
children={n:[b for b in names if b==n or n in ancestors(b)] for n in names}
def world(local):
 out={}
 for n in ordered:out[n]=out[parent[n]]@local[n] if parent[n] else ref[n].copy()
 return out
idle={n:mat(idle_data['keys'][n][0]) for n in names};idle_world=world(idle)
native=[]
for row in data['frames']:
 pose={n:mat(v) for n,v in row.items()};neutral=ref[root]@pose[root].inverted();native.append({n:neutral@m for n,m in pose.items()})
drift=native[-1]['Bone_001'].translation-native[0]['Bone_001'].translation;drift.z=0
offset=idle_world['Bone_001'].translation-native[0]['Bone_001'].translation;offset.z=0
for i,pose in enumerate(native):
 for n in children['Bone_001']:pose[n].translation+=offset-drift*(i/(len(native)-1))
native_local=[{n:pose[parent[n]].inverted()@pose[n] if parent[n] else ref[n].copy() for n in names} for pose in native]
def ease(x):
 x=min(1.,max(0.,x));return x*x*x*(10.-15.*x+6.*x*x)
# Exact phase schedule from HundredEyedSlag/RampageV8/author_rampage.py.
# This retains its slow load and rapid forward/down strike, not uniform slowing.
PHASE=[(0.,0.),(.50,.23),(.73,.39),(1.40,1.)]
def phase(t):
 for (a,x),(b,y) in zip(PHASE,PHASE[1:]):
  if t<=b:return x+(y-x)*max(0.,min(1.,(t-a)/(b-a)))
 return PHASE[-1][1]

def sample(t):
 f=min(len(native_local)-1,max(0,t*data['fps']));i=int(f);j=min(i+1,len(native_local)-1);a=f-i
 return {n:Matrix.LocRotScale(native_local[i][n].translation.lerp(native_local[j][n].translation,a),native_local[i][n].to_quaternion().slerp(native_local[j][n].to_quaternion(),a),local_ref[n].to_scale()) for n in names}
C=Matrix(((0,-100,0,0),(-100,0,0,0),(0,0,100,0),(0,0,0,1)));invC=C.inverted()
groups={g.index:g.name for g in body.vertex_groups};points=[];weights=[]
for v in body.data.vertices:
 points.append(list(C@(body.matrix_world@v.co)))
 row={groups[g.group]:g.weight for g in v.groups if groups[g.group] in ref and g.weight>1e-6};total=sum(row.values());weights.append({n:w/total for n,w in row.items()} if total else {})
points=np.array(points)
def selected(family,threshold=.65):return np.array([i for i,w in enumerate(weights) if sum(w.get(n,0.) for n in family)>threshold],dtype=int)
def skin_inputs(indices):
 p=np.c_[points[indices],np.ones(len(indices))];out={}
 for n in names:
  w=np.array([weights[i].get(n,0.) for i in indices])
  if np.any(w):out[n]=(p@np.array(inv_ref[n]).T)*w[:,None]
 return out
def skinned(pose,inputs):return sum(v@np.array(pose[n]).T for n,v in inputs.items())[:,:3]
feet=[]
for family in [{'Bone_008','Bone_007','Bone_006'},{'Bone_013','Bone_012','Bone_011'}]:
 indices=selected(family,.6);indices=indices[points[indices,2]<=np.percentile(points[indices,2],10)+.8];feet.extend(indices[::max(1,math.ceil(len(indices)/180))])
sole=skin_inputs(np.array(feet,dtype=int))
def ground(pose):
 dz=.30-float(skinned(pose,sole)[:,2].min())
 for n in names:
  if n!=root:pose[n].translation+=Vector((0,0,dz))
poses=[]
for i in range(COUNT):
 t=i/FPS;local=sample(phase(t));entry=ease(t/.24)
 for n in names:
  delay=0.
  recovery=ease((t-(1.12+delay))/(DURATION-(1.12+delay)))
  w=entry*(1-recovery);a,b=idle[n],local[n]
  local[n]=Matrix.LocRotScale(a.translation.lerp(b.translation,w),a.to_quaternion().slerp(b.to_quaternion(),w),local_ref[n].to_scale())
 pose=world(local);ground(pose);poses.append(pose)

# The complete native limb rotations are retained. The target mesh already
# carries V10's measured forearm/palm body colliders for the continuous cloth.
# A palm capsule supplements the saved forearm collider during low follow-through.
hand_ids=selected(set(children['Bone_025']),.7);hand=points[hand_ids];wrist=np.array(ref['Bone_025'].translation);center=np.mean(hand,axis=0);axis=center-wrist;axis/=np.linalg.norm(axis)
projection=(hand-wrist)@axis;radius=float(np.percentile(np.linalg.norm(hand-wrist-projection[:,None]*axis,axis=1),98))+1.
palm_a=wrist+axis*float(np.percentile(projection,20));palm_b=wrist+axis*float(np.percentile(projection,90))
# The V10 mesh, proxy, physics and cloth stay saved unchanged.
keys={n:[] for n in names};last={};forearm=[];palm=[]
for pose in poses:
 forearm.append(list(pose['Bone_026'].translation.lerp(pose['Bone_025'].translation,.60)))
 palm.append(list(pose['Bone_025']@inv_ref['Bone_025']@Vector(palm_b)))
 for n in names:
  m=pose[parent[n]].inverted()@pose[n] if parent[n] else ref[n];p,q,s=m.decompose()
  if n in last and q.dot(last[n])<0:q.negate()
  last[n]=q.copy();keys[n].append({'p':list(p),'q':[q.x,q.y,q.z,q.w],'s':list(local_ref[n].to_scale())})
(P/'Motion/attack_keys.json').write_text(json.dumps({'fps':FPS,'frames':COUNT,'keys':keys}),encoding='utf-8')
start,end,center_time=.54,.73,.635
in_contact=[i for i in range(COUNT) if start<=i/FPS<=end];reach=max(max(forearm[i][0],palm[i][0]) for i in in_contact)+radius
attack_range=max(110.,reach+34.);stop=max(65.,attack_range-28.)
manifest={'source_asset':data['source_asset'],'native_asset':data['native_asset'],'duration':DURATION,'fps':FPS,'frames':COUNT,'contact_start':start,'contact_end':end,'contact_center':center_time,'facing_lock_time':.48,'cooldown':1.1,'attack_range_cm':attack_range,'stopping_distance_cm':stop,'trace_radius_cm':radius,'forearm_trace':forearm,'palm_trace':palm,'hundred_eye_asset':data['hundred_eye_asset'],'hundred_eye_duration':data['hundred_eye_duration'],'source_time_mapping':PHASE,'manual_limb_rotation_corrections':False,'cloth_version_retained':None,'approach':'Hundred-Eyed Slag Rampage Attack_Biped_Melee_A full-body biped donor and exact 1.4-second phase schedule; native three-joint limb retarget; original rotations retained during strike; standing entry/recovery and sole height fitted to Warden; complete V14 body retained; clothing removed','game_tested':False,'rendered':False}
(P/'Records/melee_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
rig.animation_data_clear();rig.animation_data_create();action=bpy.data.actions.new('A_NightWarden_HundredEyeSweep_V12');rig.animation_data.action=action
rest_bl={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones};last={}
for i,pose in enumerate(poses,1):
 desired={n:invC@pose[n]@inv_ref[n]@C@rest_bl[n] for n in rest_bl}
 for pb in sorted(rig.pose.bones,key=lambda b:len(b.bone.parent_recursive)):
  n=pb.name;par=pb.parent;basis=pb.bone.convert_local_to_pose(desired[n],pb.bone.matrix_local,parent_matrix=desired[par.name] if par else Matrix.Identity(4),parent_matrix_local=par.bone.matrix_local if par else Matrix.Identity(4),invert=True)
  p,q,s=basis.decompose()
  if n in last and q.dot(last[n])<0:q.negate()
  last[n]=q.copy();pb.rotation_mode='QUATERNION';pb.location=p;pb.rotation_quaternion=q;pb.scale=s
  for channel in ['location','rotation_quaternion','scale']:pb.keyframe_insert(channel,frame=i,group=n)
S=bpy.context.scene;S.render.fps=FPS;S.frame_start=1;S.frame_end=COUNT;S.frame_set(1);action.use_fake_user=True
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Authoring/NightWarden_HundredEyeSweep_V12.blend'))
print('NW12_HUNDRED_EYE_SWEEP_AUTHORED '+json.dumps({'duration':DURATION,'contact':[start,end],'attack_range_cm':attack_range,'source':data['source_asset'],'hundred_eye_asset':data['hundred_eye_asset'],'manual_limb_rotation_corrections':False,'mesh_cloth':'V10 retained','game_tested':False}),flush=True)
