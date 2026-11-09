from pathlib import Path
import sys,pickle,json,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Insert30'))
import common as c
d=pickle.load(open(r/'current.pkl','rb'));c.d=d;ix=c.ix
def metrics(a):
 p=a[:,:3];q=R.from_quat(a[:,3:7]);return dict(travel_extent_cm=np.ptp(p,axis=0).tolist(),max_from_start_cm=float(np.linalg.norm(p-p[0],axis=1).max()),max_from_start_deg=float(np.degrees((q[0].inv()*q).magnitude()).max()))
report={}
for key,v in json.loads((r/'references.json').read_text()).items():report[key]=metrics(np.array(v['frames']))
for path,v in d['clips'].items():
 raw=np.array(v['frames']);t=np.array(v['times']);w=c.world(c.layer(raw,path,'base',t));p=w[:,ix['WPN_root']];a=np.c_[p[:,:3,3],R.from_matrix(p[:,:3,:3]/np.linalg.norm(p[:,:3,:3],axis=1)[:,None,:]).as_quat()]
 key='M249/'+path.split('.')[-1];report[key]=metrics(a);report[key]['root_motion']=v['root_motion']
 if '/SideMagazine'not in path:continue
 print('root parents',[(n,d['parents'][ix[n]])for n in ['root','WPN_root','clavicle_l','clavicle_r','ik_hand_root']if n in ix],flush=True)
 print('gun at idle',a[0].tolist(),'gun euler xyz',R.from_quat(a[0,3:7]).as_euler('xyz',degrees=True),flush=True)
 print('side samples',[(float(t[k]),np.round(a[k,:3],3).tolist(),np.round((R.from_quat(a[0,3:7]).inv()*R.from_quat(a[k,3:7])).as_euler('xyz',degrees=True),2).tolist())for tm in [.2,.72,1.2,1.8,2.4,2.55,2.7,2.85,3.1,3.5,3.87,4.3]for k in [int(np.argmin(abs(t-tm)))]],flush=True)
 report[key]['handoff_0.16_to_seat_motion']=metrics(a[(t>=.16)&(t<=2.76)])
(r/'diagnosis.json').write_text(json.dumps(report,indent=2))
for k,v in report.items():print(k,json.dumps(v),flush=True)
