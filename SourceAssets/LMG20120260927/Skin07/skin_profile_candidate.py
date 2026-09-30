"""Apply the existing sword elbow-cap recipe to sampled installed UE skin."""
import json,numpy as np
from scipy.spatial.transform import Rotation
from pathlib import Path
O=Path(__file__).parent;d=json.loads((O/'installed_skin.json').read_text());diag=json.loads((O/'skin_diagnosis.json').read_text())
def matrix(t):
 m=np.eye(4);m[:3,:3]=np.array(t['axes']).T;m[:3,3]=t['position'];return m
B={n:matrix(t) for n,t in d['bones'].items()};vs=np.array(d['positions']);weights=d['weights'];faces=np.array(d['triangles'])
def normalized(v):return v/np.linalg.norm(v)
def between(a,b):
 a=normalized(a);b=normalized(b);c=np.cross(a,b);s=np.linalg.norm(c)
 return Rotation.from_rotvec(c/s*np.arctan2(s,np.dot(a,b))).as_matrix() if s>1e-8 else np.eye(3)
stations={'lowerarm_l':0.,'lowerarm_twist_02_l':diag['stations']['lowerarm_twist_02_l'],'lowerarm_twist_01_l':diag['stations']['lowerarm_twist_01_l']}
axis=normalized(B['hand_l'][:3,3]-B['lowerarm_l'][:3,3]);length=np.linalg.norm(B['hand_l'][:3,3]-B['lowerarm_l'][:3,3]);along=(vs-B['lowerarm_l'][:3,3])@axis/length
ids=[i for i,w in enumerate(weights) if -.12<along[i]<.16 and sum(v for n,v in w.items() if n.endswith('_l') and n.startswith(('upperarm','lowerarm','hand_')))>.98]
def metrics(pose):
 D={n:pose[n]@np.linalg.inv(B[n]) for n in pose};dets=[];points=[]
 for i in ids:
  g=sum((w*D[n][:3,:3] for n,w in weights[i].items() if n in D),np.zeros((3,3)));dets.append(np.linalg.det(g))
  points.append(sum((w*(D[n][:3,:3]@vs[i]+D[n][:3,3]) for n,w in weights[i].items() if n in D),np.zeros(3)))
 return {'vertices':len(ids),'linear_skin_volume_p05_median':np.percentile(dets,[5,50]).tolist(),'linear_skin_volume_min':float(min(dets))}
out={'source_recipe':'RuneSword20260913/ChargedErgoV43/twist_distribution.py::forearm_roll/rebuild; stations from installed V7 skin','stations':stations,'samples':{}}
for key,poses in d['poses'].items():
 p={n:matrix(t) for n,t in poses.items()};edited={n:m.copy() for n,m in p.items()};fa=normalized(p['hand_l'][:3,3]-p['lowerarm_l'][:3,3]);up=p['upperarm_l'][:3,:3]@np.linalg.inv(B['upperarm_l'][:3,:3])
 up=Rotation.from_matrix(up).as_matrix();zero=between(up@axis,fa)@up;delta=p['lowerarm_l'][:3,:3]@np.linalg.inv(B['lowerarm_l'][:3,:3])@zero.T
 q=Rotation.from_matrix(delta).as_quat();q=q if q[3]>=0 else -q;elbow_angle=2*np.arctan2(np.dot(q[:3],fa),q[3])
 hand_delta=p['hand_l'][:3,:3]@np.linalg.inv(B['hand_l'][:3,:3])@zero.T
 q=Rotation.from_matrix(hand_delta).as_quat();q=q if q[3]>=0 else -q;angle=2*np.arctan2(np.dot(q[:3],fa),q[3])
 for n,t in stations.items():edited[n][:3,:3]=Rotation.from_rotvec(fa*angle*t).as_matrix()@zero@B[n][:3,:3]
 out['samples'][key]={'before':metrics(p),'candidate':metrics(edited),'elbow_cap_roll_before_degrees':float(np.degrees(elbow_angle)),'elbow_cap_roll_candidate_degrees':0.,'distal_roll_degrees':float(np.degrees(angle))}
 print(key,json.dumps(out['samples'][key]),flush=True)
(O/'skin_profile_candidate.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
