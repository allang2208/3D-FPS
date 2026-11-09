"""Coupled contact-space joint solve, using actual weighted skin Jacobians."""
from pathlib import Path
import runpy,pickle,numpy as np,json,sys
from mathutils import Vector
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');results=pickle.load(open(r/'idle_fit.pkl','rb'));family=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'angled';row=results[family]
fit=s['Fit'](row['old_world'],family,[n for n in s['data']['parts'][family] if 'side_mag' not in n],stride=1)
s['limits'][:3]=[5,3,3];s['limits'][3:6]=35
if family=='angled':
 for j,p in enumerate(s['params']):
  if p['label']=='flex' and '_01_' in p['bone']:s['limits'][6+j]=40
def residual(x):
 points=s['skin'](fit.pose(x));depth,near=fit.measure(points,fit.sample);ids=np.flatnonzero(depth>.025);targets=[];weights=[];selected=[]
 for i in ids:
  hits=[tree.find_nearest(Vector(points[i])) for name,tree,lo,hi in fit.trees]
  hit=min(hits,key=lambda h:abs(h[3]-depth[i]));target=np.array(hit[0]);direction=s['unit'](target-points[i]);selected.append(i);targets.append(target+direction*.045-points[i]);weights.append(8. if depth[i]>.6*depth.max() else 3.)
 for digit,mask in s['digit_groups'].items():
  choices=np.flatnonzero(mask)[::3];hits=[fit.grip.find_nearest(Vector(points[i])) for i in choices];dist=np.array([h[3] for h in hits]);nearids=np.argsort(dist)[:5]
  for j in nearids:
   if dist[j]<.14:continue
   i=choices[j];target=np.array(hits[j][0]);direction=s['unit'](target-points[i]);selected.append(i);targets.append(direction*(dist[j]-.12));weights.append(1.)
 return points,np.array(selected),np.array(targets),np.array(weights)
choices=[]
for seed in [0]:
 x=np.pad(row['parameters'],(0,len(s['limits'])-len(row['parameters'])))
 best=fit.score(x)
 for iteration in range(40):
  points,ids,targets,weights=residual(x)
  if not len(ids):break
  jac=[]
  for i in range(len(x)):
   h=.01 if i<3 else .1;trial=x.copy();trial[i]+=h;new=s['skin'](fit.pose(trial));jac.append(((new[ids]-points[ids])/h*weights[:,None]).ravel())
  J=np.array(jac).T;y=(targets*weights[:,None]).ravel();reg=np.array([.2]*3+[.025]*3+[.02]*(len(x)-6))
  step=np.linalg.solve(J.T@J+np.diag(reg*reg)+np.eye(len(x))*1e-4,J.T@y-reg*reg*x);step[:3]=np.clip(step[:3],-.6,.6);step[3:]=np.clip(step[3:],-6,6)
  found=False
  for alpha in [1.,.5,.25,.125]:
   trial=np.clip(x+alpha*step,-s['limits'],s['limits']);cost=fit.score(trial)
   if cost<best-1e-5:x,best=trial,cost;found=True;break
  if iteration%5==0:print('COUPLED_CONTACT',seed,iteration,fit.score(x,True),flush=True)
  if not found:break
 x,_,after=fit.optimize(x,[(.1,2),(.05,1)]);choices.append((fit.score(x),x));print('COUPLED_SEED',seed,after,flush=True)
score,x=min(choices,key=lambda v:v[0]);after=fit.score(x,True)
if score<fit.score(row['parameters']) or family=='canted':
 row.update(new_world=fit.root@fit.pose(x),parameters=x,after=after);pickle.dump(results,open(r/'idle_fit.pkl','wb'));(r/'idle_fit.json').write_text(json.dumps({f:{k:v for k,v in row.items() if k in ['before','after']} for f,row in results.items()},indent=2))
print('COUPLED_FINAL',after,flush=True)
(r/'parameters.json').write_text(json.dumps(s['params'],indent=2))
