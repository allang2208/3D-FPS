"""Local finger/palm clearance along the already compact magazine return."""
from pathlib import Path
import runpy,pickle,numpy as np,json,sys,os
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module')
fit_results_path=Path(os.environ.get('CONTACT25_RETURN_FILE',str(r/'return_fit.pkl')))
corrected=pickle.load(open(r/'corrected.pkl','rb'));results=pickle.load(open(fit_results_path,'rb')) if fit_results_path.exists() else {};report=json.loads((r/'return_fit.json').read_text()) if (r/'return_fit.json').exists() else {}
wanted=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
s['limits'][:3]=3.;s['limits'][3:6]=15.
for curve in results.values():
 if curve['values'].shape[1]<len(s['limits']):curve['values']=np.pad(curve['values'],((0,0),(0,len(s['limits'])-curve['values'].shape[1])))
class ReturnFit(s['Fit']):
 def pose(self,x):
  if hasattr(self,'fixed_wrist'):x=np.array(x).copy();x[:6]=self.fixed_wrist
  return super().pose(x)
 def score(self,x,details=False):
  if hasattr(self,'fixed_wrist'):x=np.array(x).copy();x[:6]=self.fixed_wrist
  points=s['skin'](self.pose(x))[self.sample];depth,_=self.measure(points,self.sample);excess=np.maximum(depth-.03,0)
  value=35*float(excess@excess)+250*float(excess.max(initial=0))**2+.4*float(x[:3]@x[:3])+.008*float(x[3:6]@x[3:6])+.0015*float(x[6:]@x[6:])
  if details:return dict(score=value,max_depth_cm=float(depth.max(initial=0)),inside_vertices=int(np.sum(depth>.12)),offset_cm=x[:3].tolist(),rotation_deg=x[3:6].tolist(),joint_max_deg=float(np.max(abs(x[6:]))))
  return value
 def optimize(self,start=None,steps=None):
  from mathutils import Vector
  x=np.zeros(len(s['limits'])) if start is None else np.pad(start,(0,len(s['limits'])-len(start)));before=self.score(x,True);best=before['score']
  for iteration in range(30):
   points=s['skin'](self.pose(x));dep,_=self.measure(points[self.sample],self.sample);ids=self.sample[dep>.03];depth=dep[dep>.03]
   if not len(ids):break
   targets=[]
   for i,distance in zip(ids,depth):
    hits=[tree.find_nearest(Vector(points[i])) for name,tree,lo,hi in self.trees];hit=min(hits,key=lambda h:abs(h[3]-distance));target=np.array(hit[0]);direction=s['unit'](target-points[i]);targets.append(target+direction*.05-points[i])
   weights=np.where(depth>depth.max()*.65,2.5,1.);J=[]
   for i in range(len(x)):
    h=.01 if i<3 else .1;trial=x.copy();trial[i]+=h;new=s['skin'](self.pose(trial));J.append(((new[ids]-points[ids])/h*weights[:,None]).ravel())
   J=np.array(J).T;y=(np.array(targets)*weights[:,None]).ravel();reg=np.array([.1]*3+[.015]*3+[.007]*(len(x)-6));step=np.linalg.solve(J.T@J+np.diag(reg*reg)+np.eye(len(x))*1e-4,J.T@y-reg*reg*x);step[:3]=np.clip(step[:3],-.4,.4);step[3:]=np.clip(step[3:],-6,6)
   found=False
   for alpha in [1.,.5,.25,.125]:
    trial=np.clip(x+step*alpha,-s['limits'],s['limits']);cost=self.score(trial)
    if cost<best-1e-5:x,best=trial,cost;found=True;break
   if not found or self.score(x,True)['max_depth_cm']<.08:break
  detail=self.score(x,True)
  if detail['max_depth_cm']>.18:
   for level in (steps or [(.1,2),(.05,1)]):
    x,_,detail=super().optimize(x,[level])
    if detail['max_depth_cm']<.12:break
  if detail['max_depth_cm']>.18 and not hasattr(self,'fixed_wrist') and not getattr(self,'searching_clearance',False):
   best_seed=(self.score(x),x.copy())
   # A closed magazine lip has separate safe sides. A small diagonal wrist
   # clearance can leave that basin while keeping the original finger shape.
   for basis in [np.zeros_like(x),x.copy()]:
    for offset in np.ndindex(3,3,3):
     trial=basis.copy();trial[:3]=np.array(offset)*2.5-2.5;value=self.score(trial)
     if value<best_seed[0]:best_seed=(value,trial)
   if best_seed[0]<self.score(x)-1e-4:
    self.searching_clearance=True
    x,_,detail=self.optimize(best_seed[1],steps)
    self.searching_clearance=False
  if detail['max_depth_cm']>.18 and hasattr(self,'fixed_wrist'):
   best=self.score(x)
   for i in range(6,len(x)):
    for value in np.linspace(-s['limits'][i],s['limits'][i],9):
     trial=x.copy();trial[i]=value;cost=self.score(trial)
     if cost<best-1e-5:x,best=trial,cost
   x,_,detail=super().optimize(x,[(.04,1.)])
  if hasattr(self,'fixed_wrist'):x[:6]=self.fixed_wrist
  print('RETURN_COUPLED',self.family,detail,flush=True)
  return x,before,detail
for (family,path),row in corrected.items():
 if '/SideMagazine' not in path:continue
 if wanted and family not in wanted:continue
 end=3.14 if path.split('.')[0].endswith('_empty') else 3.50;times=row['times'];world=row['world']
 # Source-frame keys, with exact unmodified endpoints. Additional dense sweep
 # below authoring can add only the keys which need more clearance.
 ids=sorted(set([int(np.searchsorted(times,2.76)),int(np.searchsorted(times,end))]+[int(np.argmin(abs(times-t))) for t in np.linspace(2.76,end,18)]))
 keys=[];values=[];stats=[];last=np.zeros(len(s['limits']))
 for k in ids:
  tm=times[k];zero=np.zeros(len(s['limits']));fit=ReturnFit(world[k],family,stride=3);initial=fit.score(zero,True);x=zero
  if tm>2.77 and tm<end-.006 and initial['max_depth_cm']>.12:
   choices=[zero,last];start=min(choices,key=fit.score);x,_,after=fit.optimize(start,[(.35,7),(.15,3),(.06,1.5)])
   fit.sample=np.arange(len(s['skin_ids']));full=fit.score(x,True)
   if full['max_depth_cm']>.18:x,_,full=fit.optimize(x,[(.08,2),(.04,1)])
  else:full=initial
  last=x;keys.append(float(tm));values.append(x);stats.append(dict(source=float(tm),before=initial['max_depth_cm'],after=full['max_depth_cm']))
  print('RETURN_KEY',family,path.split('/')[-1],round(float(tm),4),round(initial['max_depth_cm'],3),round(full['max_depth_cm'],3),flush=True)
 results[(family,path)]=dict(times=np.array(keys),values=np.array(values));report[family+'/'+path.split('/')[-1]]=stats
 pickle.dump(results,open(fit_results_path,'wb'));(r/'return_fit.json').write_text(json.dumps(report,indent=2))
