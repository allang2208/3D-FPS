from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'fine_fit.py'),run_name='contact_fine');FineFit=n['FineFit'];s=n['s'];data=pickle.load(open(r/'baseline.pkl','rb'))
for family,kind,tm in [('vertical','idle',0),('prism','idle',0),('angled','idle',0),('vertical','side_reload_empty',2.985096),('angled','side_reload',3.245998)]:
 key=next(k for k in data if k[0]==family and k[1].split('.')[-1]=='A_M249_'+kind);row=data[key];k=np.argmin(abs(row['times']-tm));fit=FineFit(row['world'][k],family,stride=1)
 x,before,after=fit.optimize();print('FINE_PROBE',family,kind,row['times'][k],before,after,'parameters',x.tolist(),flush=True)
