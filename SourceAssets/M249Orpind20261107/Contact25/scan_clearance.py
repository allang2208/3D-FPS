from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');rows=pickle.load(open(r/'corrected.pkl','rb'))
for (family,path),row in rows.items():
 if family!='vertical' or 'side_reload.' not in path:continue
 for q in [.50,.525,.55,.575]:
  k=np.argmin(abs(row['times']-(2.76+q*.74)));fit=s['Fit'](row['world'][k],family,stride=1);zero=np.zeros(len(s['limits']));points=s['skin'](fit.pose(zero));dep,_=fit.measure(points,fit.sample);out=[]
  for axis in range(3):
   for amount in [-3.,-2.,-1.,1.,2.,3.]:
    x=zero.copy();x[axis]=amount;d,_=fit.measure(s['skin'](fit.pose(x)),fit.sample);out.append((float(d.max()),axis,amount))
  print('CLEARANCE',q,'old',float(dep.max()),'best',sorted(out)[:6],flush=True)
