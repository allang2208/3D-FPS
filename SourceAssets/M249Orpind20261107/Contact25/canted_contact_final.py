from pathlib import Path
import runpy,pickle,numpy as np,json
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');results=pickle.load(open(r/'idle_fit.pkl','rb'));row=results['canted'];fit=s['Fit'](row['old_world'],'canted',[n for n in s['data']['parts']['canted'] if 'side_mag' not in n],stride=1)
s['limits'][:3]=4;s['limits'][3:6]=35
x=np.zeros(len(s['limits']));x[:6]=[1.98232746,2.11015133,2.56008922,-20.78861978,-11.80301377,6.49027522];best=fit.score(x)
for sweep in range(2):
 for i in range(6,len(x)):
  for value in np.linspace(-s['limits'][i],s['limits'][i],13):
   trial=x.copy();trial[i]=value;cost=fit.score(trial)
   if cost<best:best,x=cost,trial
 print('SHAFT_FINGERS',sweep,fit.score(x,True),flush=True)
x,_,after=fit.optimize(x,[(.15,3),(.075,1.5),(.035,.75)])
row.update(new_world=fit.root@fit.pose(x),parameters=x,after=after);pickle.dump(results,open(r/'idle_fit.pkl','wb'));(r/'idle_fit.json').write_text(json.dumps({f:{k:v for k,v in rr.items() if k in ['before','after']} for f,rr in results.items()},indent=2));(r/'parameters.json').write_text(json.dumps(s['params'],indent=2));print('SHAFT_FINAL',after,flush=True)
