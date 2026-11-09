"""Retain smooth, useful contact corrections without new edge crossings."""
from pathlib import Path
import runpy,pickle,numpy as np,json,sys
from mathutils import Matrix
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'guard_fit.py'),run_name='exact_contact');Fit=n['FineFit'];s=n['s'];family=sys.argv[sys.argv.index('--')+1]
data=pickle.load(open(r/'baseline.pkl','rb'));state=pickle.load(open(r/(family+'_fit.pkl'),'rb'));out={};report={}
def ease(v):
 v=np.clip(v,0,1);return v*v*v*(v*(v*6-15)+10)
def weight(w,ref,path,t):
 hand=np.linalg.inv(s['rigid'](w[s['ix']['WPN_root']]))@w[s['ix']['hand_l']]
 distance=np.linalg.norm(hand[:3,3]-ref[:3,3]);angle=Matrix(s['rot'](hand)@s['rot'](ref).T).to_quaternion().angle*180/np.pi
 a=(1-ease((distance-.5)/3.5))*(1-ease((angle-4)/28))
 if t>2.76:
  end=3.14 if '_empty' in path else 3.5;a=ease(((t-2.76)/(end-2.76)-.7)/.3)
 return float(a)
def smooth(v,sigma):
 size=int(4*sigma+.5);axis=np.arange(-size,size+1);kernel=np.exp(-.5*(axis/sigma)**2);kernel/=kernel.sum()
 return np.array([np.convolve(np.pad(col,(size,size),mode='edge'),kernel,mode='valid') for col in v.T]).T
moving=[i for i,name in enumerate(s['names']) if name.endswith('_l') and name.startswith(('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','ik_hand'))]
def contact_cost(fit,x):
 detail=fit.score(x,True);return 100000.*detail['max_depth_cm']**2+.01*detail['score'],detail
def translate(fit,start):
 x=start.copy();best,detail=contact_cost(fit,x)
 for iteration in range(12):
  points=s['skin'](fit.pose(x));depth,_=fit.measure(points,fit.sample);selected=np.flatnonzero(depth>.025)
  if not len(selected):break
  targets=np.array([fit.escape_targets[int(i)]-points[i] for i in selected]);weight=np.maximum(.2,depth[selected]/max(depth.max(),1e-8))**2;J=[]
  for axis in range(3):
   t=x.copy();t[axis]+=.01;J.append(((s['skin'](fit.pose(t))[selected]-points[selected])/.01*weight[:,None]).ravel())
  J=np.array(J).T;y=(targets*weight[:,None]).ravel();step=np.linalg.solve(J.T@J+np.eye(3)*1e-4,J.T@y);found=False
  for alpha in [1.,.5,.25]:
   t=x.copy();t[:3]+=step*alpha;length=np.linalg.norm(t[:3])
   if length>.2:t[:3]*=.2/length
   value,d=contact_cost(fit,t)
   if value<best-1e-6:x,best,detail=t,value,d;found=True;break
  if not found:break
 return x,detail
for (fam,path),row in data.items():
 if fam!=family or '/SideMagazine' not in path:continue
 times=row['times'];old=row['world'];end=3.14 if '_empty' in path else 3.5;curve=state['curves'][path]
 dense=np.linspace(2.76,end,int(np.ceil((end-2.76)*480))+1);values=np.array([np.interp(dense,curve['times'],curve['values'][:,j]) for j in range(len(state['idle']['parameters']))]).T
 values=smooth(values,.012/(dense[1]-dense[0]));values*=(ease((dense-2.76)/.025)*ease((end-dense)/.025))[:,None]
 params=np.array([np.interp(times,dense,values[:,j],left=0,right=0) for j in range(values.shape[1])]).T
 fit=Fit(old[0],family,stride=1);prepared=old.copy();result=old.copy();ids=np.flatnonzero((times>2.76)&(times<end));alphas=np.zeros(len(times));bestdepth={};before=[];after=[];guarded=0;previous=0.
 for k,t in enumerate(times):
  fit.reset(old[k]);a=weight(old[k],state['reference_hand'],path,t);prepared[k,moving]=(fit.root@fit.pose(state['idle']['parameters']*a))[moving]
 result=prepared.copy()
 for k in ids:
  fit.reset(prepared[k]);choices=[]
  for alpha in [0.,.25,.5,.75,1.]:
   cost,detail=contact_cost(fit,params[k]*alpha);choices.append((cost+.3*(alpha-previous)**2,alpha,detail['max_depth_cm']))
  _,alpha,depth=min(choices);alphas[k]=alpha;bestdepth[k]=depth;previous=alpha
  before.append(choices[-1][2])
 smoothed=smooth(alphas[:,None],2.)[:,0]
 for k in ids:
  fit.reset(prepared[k]);alpha=smoothed[k];detail=fit.score(params[k]*alpha,True)
  if detail['max_depth_cm']>bestdepth[k]+.015:
   alpha=alphas[k];detail=fit.score(params[k]*alpha,True);guarded+=1
  x=params[k]*alpha
  if detail['max_depth_cm']>.03:x,detail=translate(fit,x)
  params[k]=x;after.append(detail['max_depth_cm'])
 # The extra palm correction is sub-millimetre between adjacent samples and
 # smoothed independently of finger articulation. Both endpoints stay fixed.
 palm=smooth(params[:,:3],1.5)
 for k in ids:
  fit.reset(prepared[k]);trial=params[k].copy();trial[:3]=palm[k];detail=fit.score(trial,True)
  if detail['max_depth_cm']<=after[list(ids).index(k)]+.015:params[k]=trial
  result[k,moving]=(fit.root@fit.pose(params[k]))[moving]
 out[(path,family)]=dict(world=result,times=times)
 report[path]=dict(smoothed_candidate_max_cm=max(before),protected_max_cm=max(after),edge_guard_frames=guarded)
 print('CONTACT_PROTECTED',family,path.split('.')[-1],report[path],flush=True)
pickle.dump(out,open(r/(family+'_guarded.pkl'),'wb'));(r/(family+'_protected.json')).write_text(json.dumps(report,indent=2))
