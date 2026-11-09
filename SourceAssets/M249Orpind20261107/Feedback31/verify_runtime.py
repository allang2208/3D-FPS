"""Check receiver movement and unchanged contact geometry in native pose output."""
from pathlib import Path
import json,pickle,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;d=pickle.load(open(r/'current.pkl','rb'));ix={n:i for i,n in enumerate(d['names'])};n=len(ix);results={}
def data(folder):return np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+n*7)
def relative(pose,child):
 g=pose[:,ix['WPN_root']];p=pose[:,ix[child]];q=R.from_quat(g[:,3:]);return q.inv().apply(p[:,:3]-g[:,:3]),q.inv()*R.from_quat(p[:,3:])
for folder in sorted((r/'saved').iterdir()):
 if not(folder/'review.json').exists():continue
 old=r.parent/'Insert30/saved'/folder.name;a=data(old);b=data(folder);assert np.array_equal(a[:,:4],b[:,:4]),folder.name
 p=a[:,4:].reshape(-1,n,7);q=b[:,4:].reshape(-1,n,7);contacts={}
 for bone in ['hand_l','hand_r','lowerarm_l','lowerarm_r','PKM_Charge','WPN_SOCKET_Magazine']:
  if bone not in ix:continue
  pa,qa=relative(p,bone);pb,qb=relative(q,bone);contacts[bone]=dict(max_relative_cm=float(np.linalg.norm(pa-pb,axis=1).max()),max_relative_deg=float(np.degrees((qa.inv()*qb).magnitude()).max()))
 window=(a[:,1]>=1.05)&(a[:,1]<=2.40);motion=[]
 for pose in [p,q]:
  g=pose[window,ix['WPN_root']];rotation=R.from_quat(g[:,3:]);motion.append(dict(displacement_cm=float(np.linalg.norm(g[:,:3]-g[0,:3],axis=1).max()),rotation_deg=float(np.degrees((rotation[0].inv()*rotation).magnitude()).max())))
 results[folder.name]=dict(playback_clock_unchanged=True,relative_contacts=contacts,handling_motion_before_after=motion)
 assert all(v['max_relative_cm']<.015 and v['max_relative_deg']<.015 for v in contacts.values()),folder.name
 assert motion[1]['displacement_cm']>.20 and motion[1]['rotation_deg']>1.,folder.name
 print(folder.name,'receiver',motion,'max contact cm',max(v['max_relative_cm']for v in contacts.values()),flush=True)
assert len(results)==12
(r/'runtime_verification.json').write_text(json.dumps(results,indent=2))
