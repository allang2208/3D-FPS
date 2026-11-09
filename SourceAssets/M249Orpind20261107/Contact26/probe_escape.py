from pathlib import Path
import runpy,pickle,numpy as np,ast
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'fine_fit.py'),run_name='contact_fine');F=n['FineFit'];s=n['s'];data=pickle.load(open(r/'baseline.pkl','rb'))
line=next(x for x in (r/'probe_dynamic.log').read_text().splitlines() if 'vertical side' in x);x=np.array(ast.literal_eval(line.split('parameters ')[1]));key=next(k for k in data if k[0]=='vertical' and 'side_reload_empty.' in k[1]);row=data[key];w=row['world'][np.argmin(abs(row['times']-2.985096))];fit=F(w,'vertical',stride=1);best=fit.score(x);print('ESCAPE_BEFORE',fit.score(x,True),flush=True)
for sweep in range(2):
 for i in list(range(3))+list(range(6,len(x)))+list(range(3,6)):
  step=.06 if i<3 else (2. if i>=6 else .7)
  for direction in [-1,1]:
   trial=x.copy();trial[i]+=direction*step;trial=fit.clip(trial);cost=fit.score(trial)
   if cost<best:x,best=trial,cost
 print('ESCAPE_COORD',sweep,fit.score(x,True),flush=True)
x,before,after=fit.optimize(x);print('ESCAPE_AFTER',after,x.tolist(),flush=True)
