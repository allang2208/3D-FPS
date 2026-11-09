from pathlib import Path
import pickle, numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
r=Path(__file__).resolve().parent
helper=r.parent/'Repair20/author.py'; s={'__file__':str(helper)}
exec(compile(helper.read_text().split("outdir=r/'Motion'")[0],str(helper),'exec'),s)
d=pickle.load(open(r/'current.pkl','rb'))
names=d['names']; ix={n:i for i,n in enumerate(names)}; parents=d['parents']
world,encode,matrix,rot,unit,frame,mix,ease=[s[k] for k in ('world','encode','matrix','rot','unit','frame','mix','ease')]
bind,arm_names=s['binding']('l'); arm_ids=[ix[n] for n in arm_names]
def sample(track,t):
 ts=np.array(track['times']);v=np.array(track['values']).reshape(-1,10)
 # Serialized float keys can collapse near-identical author doubles. UE's
 # binary search selects the last key at a repeated time.
 keep=np.r_[np.diff(ts)>0,True];ts=ts[keep];v=v[keep];at=np.clip(t,ts[0],ts[-1])
 out=np.array([np.interp(at,ts,v[:,j]) for j in range(10)]).T
 out[:,3:7]=Slerp(ts,R.from_quat(v[:,3:7]))(at).as_quat() if len(ts)>1 else v[0,3:7]
 return out
def layer(raw,path,family,t):
 a=raw.copy();c=next((c for c in d['profiles'][family]['clips'] if c['base']==path),None)
 if c:
  for tr in c['tracks']:
   v=sample(tr,t);i=ix[tr['bone']]
   a[:,i,:3]+=v[:,:3];a[:,i,3:7]=(R.from_quat(v[:,3:7])*R.from_quat(a[:,i,3:7])).as_quat();a[:,i,7:]+=v[:,7:]
 return a
