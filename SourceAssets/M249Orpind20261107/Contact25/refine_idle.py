from pathlib import Path
import runpy,pickle,numpy as np,json,sys
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');results=pickle.load(open(r/'idle_fit.pkl','rb'))
rng=np.random.default_rng(25)
for family in ['angled','canted']:
 row=results[family];fit=s['Fit'](row['old_world'],family,[n for n in s['data']['parts'][family] if 'side_mag' not in n],stride=6)
 s['limits'][:3]=6;s['limits'][3:6]=45
 # The shape of a closed-loop grip creates disconnected local minima; search
 # whole-hand seeds first, then retain constrained finger articulation.
 candidates=[]
 for k in range(700):
  x=row['parameters'].copy()
  if k==0:pass
  elif k<126:x[:3]=np.array(np.unravel_index(k-1,(5,5,5)))*2-4
  else:
   x[:3]=rng.uniform(-4,4,3);x[3:6]=rng.uniform(-35,35,3)
  candidates.append((fit.score(x),x))
  if k%100==0:print('GLOBAL',family,k,min(c[0] for c in candidates),flush=True)
 choices=sorted(candidates,key=lambda q:q[0])[:3];fitted=[]
 for _,x in choices:
  xx,_,d=fit.optimize(x,[(.5,7),(.25,3),(.125,1.5),(.0625,.75)]);fitted.append((d['score'],xx))
 x=min(fitted,key=lambda q:q[0])[1];fit.sample=np.arange(len(s['skin_ids']));x,_,after=fit.optimize(x,[(.125,1.5),(.0625,.75),(.03125,.375)])
 row.update(new_world=fit.root@fit.pose(x),parameters=x,after=after)
 pickle.dump(results,open(r/'idle_fit.pkl','wb'));(r/'idle_fit.json').write_text(json.dumps({f:{k:v for k,v in row.items() if k in ['before','after']} for f,row in results.items()},indent=2))
 print('REFINED',family,after,flush=True)
