from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');rows=pickle.load(open(r/'corrected.pkl','rb'))
for (family,path),row in rows.items():
 if family!='angled' or 'side_reload.' not in path:continue
 fit=s['Fit'](row['world'][0],family,stride=1)
 for q in [.72,.74,.76,.78]:
  k=np.argmin(abs(row['times']-(2.76+q*.74)));w=row['world'][k];root=s['rigid'](w[s['ix']['WPN_root']]);p=s['skin'](np.linalg.inv(root)@w);dep,_=fit.measure(p,fit.sample)
  print('INSERT',q,[(s['names'][b],round(float(dep[s['dom']==b].max()),3)) for b in np.unique(s['dom']) if dep[s['dom']==b].max()>.12],flush=True)
