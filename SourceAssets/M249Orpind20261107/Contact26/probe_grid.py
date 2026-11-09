from pathlib import Path
import runpy,pickle,numpy as np,itertools,ast
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'local_fit.py'),run_name='local_fine');F=n['FineFit'];s=n['s'];data=pickle.load(open(r/'baseline.pkl','rb'))
for family,kind,tm in [('vertical','side_reload_empty',2.985096),('angled','side_reload',3.245998)]:
 key=next(k for k in data if k[0]==family and k[1].split('.')[-1]=='A_M249_'+kind);row=data[key];w=row['world'][np.argmin(abs(row['times']-tm))];fit=F(w,family,stride=1)
 x=np.zeros(len(n['limits']));best=fit.score(x);before=fit.score(x,True)
 for angles in itertools.product([-1.5,0,1.5],repeat=3):
  t=x.copy();t[3:6]=angles;t=fit.clip(t);v=fit.score(t)
  if v<best:x,best=t,v
 for direction in itertools.product([-1,0,1],repeat=3):
  t=x.copy();t[:3]=np.array(direction)*.08;t=fit.clip(t);v=fit.score(t)
  if v<best:x,best=t,v
 x,_,after=fit.optimize(x)
 for step in [4.,2.,1.,.5]:
  for sweep in range(2):
   for i in list(range(6,len(x)))+list(range(3,6))+list(range(3)):
    for direction in [-1,1]:
     t=x.copy();t[i]+=direction*(step if i>=6 else step*.25 if i>=3 else .02);t=fit.clip(t);v=fit.score(t)
     if v<best:x,best=t,v
  print('GRID_PROGRESS',family,step,fit.score(x,True),flush=True)
 print('GRID_RESULT',family,before,fit.score(x,True),x.tolist(),flush=True)
