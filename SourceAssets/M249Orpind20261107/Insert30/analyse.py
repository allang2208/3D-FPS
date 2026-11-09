from pathlib import Path
import sys,pickle,json,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent
helpers=r.parent/'Repair20/author.py';s={'__file__':str(helpers)}
exec(compile(helpers.read_text().split("outdir=r/'Motion'")[0],str(helpers),'exec'),s)
source=Path(sys.argv[1]) if len(sys.argv)>1 else r/'current.pkl'
d=pickle.load(open(source,'rb'));s['d']=d;names=d['names'];ix={n:i for i,n in enumerate(names)}
report={}
for path,c in d['clips'].items():
 if '/SideMagazine' not in path:continue
 t=np.array(c.get('times',np.arange(len(c['frames']))/c['fps']));raw=np.array(c['frames'])
 for family in d['profiles']:
  import common
  common.d=d
  local=common.layer(raw,path,family,t);w=s['world'](local);region=np.flatnonzero((t[:-1]>=2.3)&(t[:-1]<=3.3));metrics={}
  for n in ['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']:
   i=ix[n];rot=R.from_matrix(w[:,i,:3,:3]/np.linalg.norm(w[:,i,:3,:3],axis=1)[:,None,:]);step=np.degrees((rot[:-1].inv()*rot[1:]).magnitude());delta=np.linalg.norm(np.diff(w[:,i,:3,3],axis=0),axis=1);k=region[np.argmax(step[region])]
   metrics[n]=dict(rotation_step_deg=float(step[k]),source=float(t[k]),position_step_cm=float(delta[region].max()))
  key=family+'/'+path.split('.')[-1];report[key]=metrics
  peaks=sorted([(v['rotation_step_deg'],n,v['source']) for n,v in metrics.items()],reverse=True)
  print(key,peaks[:3],flush=True)
(r/('diagnosis_'+source.parent.name+'.json')).write_text(json.dumps(report,indent=2))
