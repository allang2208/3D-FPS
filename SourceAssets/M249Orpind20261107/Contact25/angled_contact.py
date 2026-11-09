from pathlib import Path
import pickle,runpy,numpy as np,json
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');results=pickle.load(open(r/'idle_fit.pkl','rb'));row=results['angled'];fit=s['Fit'](row['old_world'],'angled',[n for n in s['data']['parts']['angled'] if 'side_mag' not in n],stride=1)
s['limits'][:3]=[4,2.5,2.5];s['limits'][3:6]=30
x=np.zeros(len(s['limits']));x[0]=2.5;best=fit.score(x)
for sweep in range(3):
 for i in list(range(6,len(x)))+list(range(6)):
  for value in np.linspace(-s['limits'][i],s['limits'][i],13):
   trial=x.copy();trial[i]=value;score=fit.score(trial)
   if score<best:best,x=score,trial
 print('ANGLED_CONTACT_RANGE',sweep,fit.score(x,True),flush=True)
x,_,after=fit.optimize(x,[(.25,4),(.125,2),(.0625,1),(.03125,.5)])
if after['score']<fit.score(row['parameters']):
 row.update(new_world=fit.root@fit.pose(x),parameters=x,after=after);pickle.dump(results,open(r/'idle_fit.pkl','wb'));(r/'idle_fit.json').write_text(json.dumps({f:{k:v for k,v in row.items() if k in ['before','after']} for f,row in results.items()},indent=2))
print('ANGLED_CONTACT_FINAL',after,flush=True)
