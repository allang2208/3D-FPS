"""Diagnose actual installed skin deformation, not only preserved bone matrices."""
import json,numpy as np
from scipy.spatial.transform import Rotation
from pathlib import Path
O=Path(__file__).parent;d=json.loads((O/'installed_skin.json').read_text())
def mat(t):
 m=np.eye(4);m[:3,:3]=np.array(t['axes']).T;m[:3,3]=t['position'];return m
B={n:mat(t) for n,t in d['bones'].items()};vertices=np.array(d['positions']);weights=d['weights']
def norm(v):return v/np.linalg.norm(v)
def between(a,b):
 a=norm(a);b=norm(b);cross=np.cross(a,b);dot=np.dot(a,b)
 return Rotation.from_rotvec(norm(cross)*np.arctan2(np.linalg.norm(cross),dot)).as_matrix() if np.linalg.norm(cross)>1e-7 else np.eye(3)
def roll(D,axis):
 q=Rotation.from_matrix(D).as_quat();q=q if q[3]>=0 else -q
 return np.degrees(2*np.arctan2(np.dot(q[:3],axis),q[3]))
fore=['lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l'];upper=['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l']
dom=[max(w,key=w.get) if w else '' for w in weights];axis=norm(B['hand_l'][:3,3]-B['lowerarm_l'][:3,3]);length=np.linalg.norm(B['hand_l'][:3,3]-B['lowerarm_l'][:3,3]);along=(vertices-B['lowerarm_l'][:3,3])@axis/length
indices=[i for i,w in enumerate(weights) if sum(v for n,v in w.items() if n in fore)>.98 and -.02<along[i]<1.01]
stations={n:float(np.median(along[[i for i,x in enumerate(dom) if x==n]])) for n in fore}
report={'stations':stations,'poses':{},'source':'actual UE asset native binding and COMPRESSED animation samples'}
for key,poses in d['poses'].items():
 P={n:mat(t) for n,t in poses.items()};D={n:P[n]@np.linalg.inv(B[n]) for n in P};fa=norm(P['hand_l'][:3,3]-P['lowerarm_l'][:3,3]);ref=axis
 up=D['upperarm_l'][:3,:3];zero=between(up@ref,fa)@up
 rolls={n:roll(D[n][:3,:3]@zero.T,fa) for n in fore}
 dets=[]
 for i in indices:
  gradient=sum((v*D[n][:3,:3] for n,v in weights[i].items() if n in D),np.zeros((3,3)))
  dets.append(np.linalg.det(gradient))
 dets=np.array(dets);slice_stats={}
 for lo,hi in [(-.02,.15),(.15,.4),(.4,.7),(.7,1.01)]:
  vv=dets[(along[indices]>=lo)&(along[indices]<hi)]
  slice_stats[f'{lo}:{hi}']={'count':len(vv),'det_p05_median':np.percentile(vv,[5,50]).tolist(),'minimum':float(vv.min())} if len(vv) else {}
 report['poses'][key]={'forearm_roll_degrees':rolls,'skin_linear_volume':slice_stats}
 print(key,'ROLL',rolls,'SKIN',slice_stats,flush=True)
print('STATIONS',stations,flush=True)
reference=O.parent.parent/'ModularOutfit20260924/NativeSkin/AKM_source.json'
if reference.exists():
 orig=json.loads(reference.read_text());report['native_bind_max_element_difference']=max(float(np.max(np.abs(B[n]-mat(t)))) for n,t in orig['bones'].items() if n in B)
 print('NATIVE_BIND_DIFF',report['native_bind_max_element_difference'],flush=True)
(O/'skin_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
