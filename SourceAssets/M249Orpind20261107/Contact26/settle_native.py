from pathlib import Path
import runpy,pickle,numpy as np,sys
from mathutils import Matrix
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'guard_fit.py'),run_name='exact_native');F=n['FineFit'];s=n['s'];family=sys.argv[sys.argv.index('--')+1]
data=[v for v in pickle.load(open(r/'native_contacts.pkl','rb')) if v['family']==family];out={};prior=pickle.load(open(r/(family+'_native.pkl'),'rb'))
limits=np.array([0.,0.,0.,2.5,2.5,2.5]+[18. if p['label']=='flex' else 10. for p in s['params']])
class NativeFit(F):
 def score(self,x,details=False):
  detail=super().score(x,True);detail['score']+=192000.*detail['max_depth_cm']**2
  return detail if details else detail['score']
 def clip(self,x,rotate=True,translate=True):
  x=np.clip(x,-limits,limits);length=np.linalg.norm(x[3:6])
  if length>3:x[3:6]*=3/length
  return x
 def optimize(self,start=None):
  x=np.zeros(len(limits)) if start is None else self.clip(start);best=self.score(x);initial=self.score(x,True)
  points=s['skin'](self.pose(x));depth,_=self.measure(points,self.sample)
  affected=set()
  for i in np.flatnonzero(depth>.025):
   for bone,weight in s['g']['weights'][s['skin_ids'][i]]:
    if weight>.05:affected.add(s['names'][bone].split('_')[0])
  active=[6+i for i,p in enumerate(s['params']) if p['bone'].split('_')[0] in affected]+[3,4,5]
  for iteration in range(16):
   points=s['skin'](self.pose(x));dep,_=self.measure(points,self.sample);ids=np.flatnonzero(dep>.025)
   if not len(ids):break
   targets=np.array([self.escape_targets[int(i)]-points[i] for i in ids]);weight=np.maximum(.025,dep[ids]/max(dep.max(),1e-8))**3;J=[]
   for i in active:
    trial=x.copy();trial[i]+=.04;J.append(((s['skin'](self.pose(trial))[ids]-points[ids])/.04*weight[:,None]).ravel())
   J=np.array(J).T;y=(targets*weight[:,None]).ravel();step=np.linalg.solve(J.T@J+np.eye(len(active))*.00004,J.T@y);step=np.clip(step,-2,2);found=False
   for alpha in [1.,.5,.25]:
    trial=x.copy();trial[active]+=step*alpha;trial=self.clip(trial);cost=self.score(trial)
    if cost<best-1e-6:x,best=trial,cost;found=True;break
   if not found:break
  if self.score(x,True)['max_depth_cm']>.05:
   for step in [3.,1.]:
    for i in active:
     for sign in [-1,1]:
      trial=x.copy();trial[i]+=sign*(step if i>=6 else .4);trial=self.clip(trial);cost=self.score(trial)
      if cost<best-1e-6:x,best=trial,cost
  return x,initial,self.score(x,True)
fit=NativeFit(data[0]['world'],family,stride=1)
for path in sorted({v['path'] for v in data}):
 rows=sorted([v for v in data if v['path']==path],key=lambda v:v['time']);previous=np.zeros(len(limits));out[path]=[]
 for row in rows:
  fit.reset(row['world']);zero=np.zeros(len(limits));before=fit.score(zero,True)
  previous_entry=min(prior[path],key=lambda v:abs(v['time']-row['time']))
  if previous_entry['after']['max_depth_cm']>.045:
   x,_,after=fit.optimize(previous_entry['parameters'])
   if after['max_depth_cm']>previous_entry['after']['max_depth_cm']:
    x=previous_entry['parameters'];after=previous_entry['after']
  else:x=previous_entry['parameters'];after=previous_entry['after']
  previous=x;new=fit.root@fit.pose(x)
  out[path].append(dict(time=row['time'],before_world=row['world'],after_world=new,before=before,after=after,parameters=x))
  print('NATIVE_SETTLE',family,path.split('.')[-1],round(row['time'],6),round(before['max_depth_cm'],4),'->',round(after['max_depth_cm'],4),flush=True)
 pickle.dump(out,open(r/(family+'_native.pkl'),'wb'))
print('NATIVE_SETTLE_COMPLETE',family,flush=True)
