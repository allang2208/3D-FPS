"""Find one coherent palm clearance for both reloads, instead of isolated nudges."""
from pathlib import Path
import runpy,pickle,numpy as np,json
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');rows=pickle.load(open(r/'corrected.pkl','rb'));queries=[]
def ease(v):
 v=np.clip(v,0,1);return v*v*v*(v*(v*6-15)+10)
def gain(q):return ease((q-.32)/.13)*(1-ease((q-.6)/.12))
for (family,path),row in rows.items():
 if family!='canted' or '/SideMagazine' not in path:continue
 end=3.14 if path.split('.')[0].endswith('_empty') else 3.5
 for q in [.40,.45,.50,.525,.55,.60,.65]:
  k=np.argmin(abs(row['times']-(2.76+q*(end-2.76))));fit=s['Fit'](row['world'][k],family,stride=6);queries.append((fit,gain(q),q))
best=[]
for triple in np.ndindex(5,5,5):
 v=np.array(triple)*1.5-3
 if np.linalg.norm(v)>4.5:continue
 peak=0.;body=0.;total=0.
 for fit,weight,q in queries:
  x=np.zeros(len(s['limits']));x[:3]=v*weight;p=s['skin'](fit.pose(x))[fit.sample];dep,_=fit.measure(p,fit.sample);peak=max(peak,float(dep.max()));total+=float(np.maximum(dep-.03,0)@np.maximum(dep-.03,0));mask=np.array([s['names'][b]=='hand_l' or 'metacarpal' in s['names'][b] for b in s['dom'][fit.sample]]);body=max(body,float(dep[mask].max(initial=0)))
 score=1000*body*body+100*peak*peak+5*total+.1*float(v@v);best.append((score,v.tolist(),peak,body))
best.sort();(r/'canted_corridor.json').write_text(json.dumps(best[:12],indent=2));print('CANTED_CORRIDOR',best[:5],flush=True)
