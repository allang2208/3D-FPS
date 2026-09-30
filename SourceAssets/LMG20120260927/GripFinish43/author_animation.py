"""Bake a measured right-hand contact correction with fixed arm bone lengths."""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent;(O/'AnimationKeys').mkdir(exist_ok=True);inputs=json.loads((O/'animation_inputs.json').read_text());reference=json.loads((O/'pose_inputs.json').read_text())['clips']['idle']['bones']['hand_r'];anchor=np.array(reference['p']);delta=np.array([-.010,-.033,-.030]);out={}
def unit(v):return v/max(np.linalg.norm(v),1e-12)
def between(a,b):
 a=unit(a);b=unit(b);q=np.r_[np.cross(a,b),1+np.dot(a,b)];return R.from_quat(q/np.linalg.norm(q))
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
for path,info in inputs.items():
 data=json.loads(Path(info['file']).read_text());keys={n:[] for n in ['upperarm_r','lowerarm_r','hand_r']};weights=[]
 for frame in data['frames']:
  worlds=frame['world'];locals_=frame['local'];p=[np.array(t[:3]) for t in worlds];r=[R.from_quat(t[3:7]) for t in worlds];s=[np.array(t[7:]) for t in worlds]
  rel=r[0].inv().apply(p[4]-p[0])/s[0];distance=np.linalg.norm(rel-anchor);w=1-smooth((distance-.018)/.050);weights.append(float(w))
  if w>1e-6:
   A,B,H=p[2],p[3],p[4];goal=H+r[0].apply(delta*s[0])*w;L1=np.linalg.norm(B-A);L2=np.linalg.norm(H-B);dvec=goal-A;d=np.linalg.norm(dvec);axis=unit(dvec);d=np.clip(d,abs(L1-L2)+1e-5,L1+L2-1e-5);goal=A+axis*d
   pole=unit((B-A)-axis*np.dot(B-A,axis));along=(L1*L1-L2*L2+d*d)/(2*d);height=np.sqrt(max(0,L1*L1-along*along));elbow=A+axis*along+pole*height
   upper=between(B-A,elbow-A)*r[2];lower=between(H-B,goal-elbow)*r[3];hand=r[4];qs=[(r[1].inv()*upper).as_quat(),(upper.inv()*lower).as_quat(),(lower.inv()*hand).as_quat()]
  else:qs=[np.array(locals_[i][3:7]) for i in [2,3,4]]
  for n,i,q in zip(keys,[2,3,4],qs):
   if keys[n] and np.dot(q,keys[n][-1][3:7])<0:q=-q
   keys[n].append(locals_[i][:3]+q.tolist()+locals_[i][7:])
 tag=hashlib.sha1(path.encode()).hexdigest()[:12];file=O/'AnimationKeys'/(tag+'.json');file.write_text(json.dumps(keys,separators=(',',':')));out[path]={'sha256_before':info['sha256'],'file':str(file),'frames':len(weights),'contact_frames':sum(w>.99 for w in weights),'released_frames':sum(w<.001 for w in weights)}
(O/'animations.json').write_text(json.dumps({'delta_weapon_root_ue_m':delta.tolist(),'clips':out,'bone_lengths_changed':False,'mechanical_tracks_changed':False},indent=2));print('G43_ANIMATIONS_AUTHORED',len(out),flush=True)
