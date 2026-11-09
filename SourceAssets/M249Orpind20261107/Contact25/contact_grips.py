from pathlib import Path
import pickle,runpy,numpy as np,json
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');results=pickle.load(open(r/'idle_fit.pkl','rb'));rng=np.random.default_rng(251)
for family in ['canted','angled']:
 row=results[family];s['limits'][:3]=3;s['limits'][3:6]=35
 fit=s['Fit'](row['old_world'],family,[n for n in s['data']['parts'][family] if 'side_mag' not in n],stride=3)
 trials=[]
 for k in range(500):
  x=np.zeros(len(s['limits']))
  if k>0:x[:3]=rng.uniform(-3,3,3);x[3:6]=rng.uniform(-30,30,3)
  trials.append((fit.score(x),x))
  if k%100==0:print('CONTACT_SEED',family,k,min(v[0] for v in trials),flush=True)
 fitted=[]
 for _,x in sorted(trials,key=lambda t:t[0])[:3]:
  x,_,_=fit.optimize(x,[(.4,6),(.2,3),(.1,1.5),(.05,.75)]);fit.sample=np.arange(len(s['skin_ids']));fitted.append((fit.score(x),x));fit.sample=np.arange(0,len(s['skin_ids']),3)
 fit.sample=np.arange(len(s['skin_ids']));x=min(fitted,key=lambda t:t[0])[1];x,_,after=fit.optimize(x,[(.15,3),(.075,1.5),(.0375,.75)])
 row.update(new_world=fit.root@fit.pose(x),parameters=x,after=after);pickle.dump(results,open(r/'idle_fit.pkl','wb'));(r/'idle_fit.json').write_text(json.dumps({f:{k:v for k,v in row.items() if k in ['before','after']} for f,row in results.items()},indent=2));print('CONTACT_RESULT',family,after,flush=True)
