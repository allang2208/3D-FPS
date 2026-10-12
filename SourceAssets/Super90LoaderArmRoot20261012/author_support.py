"""Local shoulder clearance on current empty-loader clips; source hand contact stays fixed."""
from arm_core import *
from copy import deepcopy
CLEARANCE=10.;FPS=60
cm=camera()
def track(n,values):
 v=np.array(values)
 for i in range(1,len(v)):
  if np.dot(v[i-1,3:7],v[i,3:7])<0:v[i,3:7]*=-1
 constant=np.max(abs(v-v[0]))<1e-9
 return dict(bone=n,times=[0.] if constant else (np.arange(len(v))/FPS).tolist(),values=v[0].tolist() if constant else v.ravel().tolist())
def samples(t,times):
 if not t:return np.tile([0,0,0,0,0,0,1,0,0,0],(len(times),1)).astype(float)
 ts=np.array(t['times']);v=np.array(t['values']).reshape(-1,10)
 if len(ts)==1:return np.repeat(v,len(times),axis=0)
 times=np.clip(times,ts[0],ts[-1]);out=np.array([np.interp(times,ts,v[:,i]) for i in range(10)]).T
 out[:,3:7]=Slerp(ts,R.from_quat(v[:,3:7]))(times).as_quat();return out
out=dict(revision='Super90-Loader-LeftArmRoot-20261012',fps=FPS,write_bones=CHANGED,clips={},
 profiles={f:dict(path=d['path'],clips={}) for f,d in D['profiles'].items()},runtime_tested=False)
notes=dict(scope='Empty loader counts 1-7 and four grip overlays; source frames 125-160 only',
 shoulder_clearance_plane_cm=CLEARANCE,fade_frames=[125,137,145,160],
 contact='Wrist and fingers remain at their installed component-space transforms',
 geometry='Shoulder moves around the fixed wrist at the original shoulder-wrist distance; original segment lengths and elbow bend retained',
 mesh_bind_weights_changed=False,clip_durations_changed=False,runtime_tested=False,source_pose={},authored_pose={})
for role,clip in D['clips'].items():
 if not role.startswith('empty_'):continue
 base=posed(role);raw=[{n:np.array(v) for n,v in row.items()} for row in clip['rows']]
 for frame in range(126,160):
  corrected=shoulder_under_frame(base[frame],frame,CLEARANCE,cm)
  for n in CHANGED:raw[frame][n]=pack(np.linalg.inv(corrected.get(PARENTS[n],I))@corrected[n])
  if role=='empty_7' and frame in (136,140,144,148,152,156):
   notes['source_pose'][frame]=measure(base[frame],cm);notes['authored_pose'][frame]=measure(corrected,cm)
 spec=dict(path=clip['path'],source_sha256=clip['sha256'],frames=clip['frames'],duration=clip['duration'],
  tracks=[track(n,[row[n] for row in raw]) for n in NAMES])
 out['clips'][role]=spec
 for family in D['profiles']:
  source=D['profiles'][family]['clips'][clip['path']];layer=deepcopy(source)
  old={t['bone']:t for t in source['tracks']};new={t['bone']:t for t in layer['tracks']}
  actual=posed(role,family);changed={n:samples(old.get(n),clip['times']) for n in CHANGED}
  for frame in range(126,160):
   corrected=shoulder_under_frame(actual[frame],frame,CLEARANCE,cm)
   for n in CHANGED:
    desired=pack(np.linalg.inv(corrected.get(PARENTS[n],I))@corrected[n]);b=raw[frame][n]
    q=(R.from_quat(desired[3:7])*R.from_quat(b[3:7]).inv()).as_quat()
    if q[3]<0:q*=-1
    changed[n][frame]=np.r_[desired[:3]-b[:3],q,desired[7:]-b[7:]]
  for n,v in changed.items():new[n]=track(n,v)
  layer['tracks']=list(new.values());out['profiles'][family]['clips'][clip['path']]=layer
 print('ARM_ROOT_AUTHORED',role,clip['frames'],flush=True)
(O/'animation_patch.json').write_text(json.dumps(out,separators=(',',':')))
(O/'authoring.json').write_text(json.dumps(notes,indent=2))
