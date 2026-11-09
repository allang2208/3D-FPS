from pathlib import Path
import numpy as np,json,pickle
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;d=pickle.load(open(r.parent/'Repair20/native.pkl','rb'));names=d['names'];out={}
import sys
for label in sys.argv[1:]:
 records={}
 for folder in (r/label).iterdir():
  if not (folder/'review.json').exists():continue
  j=json.loads((folder/'review.json').read_text());n=j['bone_count'];raw=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+n*7);time,src=raw[:,0],raw[:,1];w=raw[:,4:].reshape(-1,n,7);rec={}
  for side in ['l','r']:
   vals={}
   for b in ['upperarm','upperarm_twist_02','lowerarm','lowerarm_twist_01','hand']:
    q=w[:,names.index(b+'_'+side),3:7];rot=R.from_quat(q);step=np.degrees((rot[:-1].inv()*rot[1:]).magnitude());dist=np.linalg.norm(np.diff(w[:,names.index(b+'_'+side),:3],axis=0),axis=1);k=step.argmax();vals[b]=dict(step_deg=float(step[k]),source=float(src[k]),runtime=float(time[k]),translation_step_cm=float(dist.max()))
   rec[side]=vals
  frames=j['frames'];rot=R.from_quat([f['camera'][3:7] for f in frames]);rec['camera_peak_deg']=float(np.degrees(rot.magnitude()).max());rec['camera_peak_cm']=float(np.linalg.norm([f['camera'][:3] for f in frames],axis=1).max());records[folder.name]=rec
 out[label]=records
(r/'motion_metrics.json').write_text(json.dumps(out,indent=2))
for label,rows in out.items():
 print(label,'cases',len(rows))
 for key in ['box_normal_base_player','box_empty_base_player','box_normal_angled_left','box_empty_angled_left','45_empty_base_player']:
  if key not in rows:continue
  x=rows[key];print(key,'hand_l',x['l']['hand'],'arm peak',max((b['step_deg'],s,n,b['source']) for s in ['l','r'] for n,b in x[s].items()),'camera',x['camera_peak_deg'],x['camera_peak_cm'])
