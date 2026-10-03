from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation as R
P=Path(__file__).resolve().parent;rest=json.loads((P/'Inputs/bare.json').read_text())['bones'];index={v['index']:n for n,v in rest.items()};parents={n:index.get(v['parent']) for n,v in rest.items()}
def mat(v):
 m=np.eye(4);m[:3,:3]=R.from_quat(v['q']).as_matrix()*np.array(v['s']);m[:3,3]=v['p'];return m
rm={n:mat(v) for n,v in rest.items()};lr={n:np.linalg.inv(rm[parents[n]])@m if parents[n] else m for n,m in rm.items()}
def ramp(t,a,b):
 x=np.clip((t-a)/(b-a),0,1);return x*x*x*(x*(x*6-15)+10)
limits={'index_03_r':(-46,.65),'thumb_03_r':(-45,.6),'middle_03_r':(-42,.85),'ring_03_r':(-40,.85),'pinky_03_r':(-38,.85)}
for family in ['base','vertical','canted','prism','angled']:
 clip=json.loads((P/'Inputs'/f'{family}.json').read_text());tracks={n:[] for n in limits};previous={n:None for n in limits};fps=(len(clip['frames'])-1)/clip['duration']
 for i,row in enumerate(clip['frames']):
  t=i/fps;w=ramp(t,4.99,5.13)*(1-ramp(t,5.835,6.04));pressure=2*ramp(t,5.13,5.36)*(1-ramp(t,5.48,5.82))
  for n,(bend,offaxis) in limits.items():
   local=np.linalg.inv(mat(row[parents[n]]))@mat(row[n]);scale=np.linalg.norm(local[:3,:3],axis=0);rot=R.from_matrix(local[:3,:3]/scale);ref=R.from_matrix(lr[n][:3,:3]);v=(ref.inv()*rot).as_rotvec();target=v.copy();target[:2]*=offaxis;target[2]=np.radians(bend-(pressure if n.startswith(('index','middle')) else .5*pressure));desired=ref*R.from_rotvec(target);q=(rot*R.from_rotvec((rot.inv()*desired).as_rotvec()*w)).as_quat()
   if previous[n] is not None and q@previous[n]<0:q=-q
   previous[n]=q;tracks[n].append(dict(p=local[:3,3].tolist(),q=q.tolist(),s=scale.tolist()))
 (P/'Authored'/f'{family}.json').write_text(json.dumps(dict(asset=clip['asset'],source_sha256=clip['source_sha256'],keys=len(clip['frames']),duration=clip['duration'],tracks=tracks,revision='RightHand52'),separators=(',',':')));print('HAND_AUTHORED',family)
