from pathlib import Path
import runpy,pickle,numpy as np
from mathutils import Matrix
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'fine_fit.py'),run_name='contact_fine');F=n['FineFit'];s=n['s'];data=pickle.load(open(r/'baseline.pkl','rb'))
for family,kind,tm in [('vertical','side_reload_empty',2.985096),('angled','side_reload',3.245998)]:
 key=next(k for k in data if k[0]==family and k[1].split('.')[-1]=='A_M249_'+kind);row=data[key];w=row['world'][np.argmin(abs(row['times']-tm))];idle=next(v['world'][0] for k,v in data.items() if k[0]==family and k[1].split('.')[-1]=='A_M249_idle');goal={i:np.linalg.inv(idle[s['parents'][i]])@idle[i] for i in s['finger_ids']};local={i:np.linalg.inv(w[s['parents'][i]])@w[i] for i in s['finger_ids']};fit=F(w,family,stride=1)
 best=(fit.score(np.zeros(len(n['limits']))),w.copy(),{})
 for finger in ['thumb','index','middle','ring','pinky']:
  start=best[1].copy()
  for alpha in [.25,.5,.75,1.]:
   trial=start.copy()
   for i in s['finger_ids']:
    if not s['names'][i].startswith(finger):continue
    loc=local[i].copy();a=Matrix(s['rot'](local[i])).to_quaternion();b=Matrix(s['rot'](goal[i])).to_quaternion();loc[:3,:3]=np.array(a.slerp(b,alpha).to_matrix())*np.linalg.norm(loc[:3,:3],axis=0);trial[i]=trial[s['parents'][i]]@loc
   fit.reset(trial);cost=fit.score(np.zeros(len(n['limits'])))
   if cost<best[0]:best=(cost,trial,best[2]|{finger:alpha})
 fit.reset(best[1]);x,before,after=fit.optimize();print('REFERENCE_RESULT',family,best[2],before,after,flush=True)
