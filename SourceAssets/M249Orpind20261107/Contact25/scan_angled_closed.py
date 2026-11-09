from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');rows=pickle.load(open(r/'corrected.pkl','rb'));goal=pickle.load(open(r/'idle_fit.pkl','rb'))['angled']['new_world'];local={i:np.linalg.inv(goal[s['parents'][i]])@goal[i] for i in s['finger_ids']}
for (family,path),row in rows.items():
 if family!='angled' or '/SideMagazine' not in path:continue
 end=3.14 if path.split('.')[0].endswith('_empty') else 3.5;fit=s['Fit'](row['world'][0],family,stride=1);out=[]
 for q in [.65,.70,.72,.74,.76,.78,.8,.85,.9]:
  tm=2.76+q*(end-2.76);k=np.argmin(abs(row['times']-tm));w=row['world'][k].copy();root=s['rigid'](w[s['ix']['WPN_root']])
  for i in s['finger_ids']:w[i]=w[s['parents'][i]]@local[i]
  dep,_=fit.measure(s['skin'](np.linalg.inv(root)@w),fit.sample);out.append((round(q,2),round(float(dep.max()),3)))
 print('CLOSED_INSERT',path.split('/')[-1],out,flush=True)
