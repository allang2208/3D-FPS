from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');Fit=s['Fit'];poses=s['poses'];skin=s['skin'];names=s['names'];dom=s['dom'];ix=s['ix'];data=s['data'];result=pickle.load(open(r/'idle_fit.pkl','rb'))['angled'];w=result['old_world'];x=result['parameters'];fit=Fit(w,'angled',obstacles=[n for n in data['parts']['angled'] if 'side_mag' not in n],stride=1)
points=skin(fit.pose(x));dep,near=fit.measure(points,fit.sample)
for k in np.argsort(dep)[-20:]:print(names[dom[k]],round(float(dep[k]),3),points[k].round(3).tolist())
for i,v in enumerate(x):
 if abs(v)>.1:print('param',i,(s['params'][i-6]['bone']+' '+s['params'][i-6]['label']) if i>=6 else 'wrist',v)
