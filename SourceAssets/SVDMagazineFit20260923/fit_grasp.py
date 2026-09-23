"""Adapt the accepted front-fingers/rear-thumb direction to the actual short SVD.
Uses continuous outer sections, fixed donor pad regions and all glove surfaces.
No translations, scaling, rest changes or per-vertex skin edits.
"""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
O=Path(__file__).parent;S=O.parent
d=json.loads((S/'RifleMagazineGrip20260922/fit_input.json').read_text())
don=json.loads((S/'RifleMagazineGrip20260922/IndexClearanceV4/selected_grasp.json').read_text())['AKM']
target=json.loads((O/'geometry_input.json').read_text())['magazine']
names=d['names'];parents=d['parents'];rest={n:np.array(m) for n,m in d['rest'].items()}
local={n:np.linalg.inv(rest[parents[n]])@rest[n] for n in names[1:]}
verts=np.c_[d['vertices'],np.ones(len(d['vertices']))]
weights=np.array([[w.get(n,0) for n in names] for w in d['weights']]);weights/=weights.sum(1)[:,None]
bound=np.array([verts@np.linalg.inv(rest[n]).T for n in names]);labels=np.array(d['labels'])
faces=np.array([[f[0],f[j],f[j+1]] for f in d['faces'] for j in range(1,len(f)-1)])
edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
def rot(q):return R.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
def wxyz(m):
 q=R.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
def unit(v):return v/np.linalg.norm(v)
class Shell:
 def __init__(self,mag):
  vs=np.array(mag['vertices']);tri=np.array([[f[0],f[j],f[j+1]] for f in mag['faces'] for j in range(1,len(f)-1)])
  self.z=np.linspace(vs[:,2].min()+1e-6,vs[:,2].max()-1e-6,128);self.low=vs[:,2].min();self.high=vs[:,2].max()
  angle=np.linspace(0,2*np.pi,48,endpoint=False);self.N=np.c_[np.cos(angle),np.sin(angle)];support=[]
  aa=vs[tri].reshape(-1,3);bb=np.roll(vs[tri],-1,axis=1).reshape(-1,3)
  for z in self.z:
   use=(aa[:,2]-z)*(bb[:,2]-z)<0;a=aa[use];b=bb[use];t=(z-a[:,2])/(b[:,2]-a[:,2]);cross=a[:,:2]+t[:,None]*(b-a)[:,:2]
   support.append(np.max(cross@self.N.T,axis=0))
  self.support=np.array(support)
 def clearance(self,p):
  hi=np.clip(np.searchsorted(self.z,p[:,2]),1,len(self.z)-1);lo=hi-1;t=np.clip((p[:,2]-self.z[lo])/(self.z[hi]-self.z[lo]),0,1)
  supp=self.support[lo]*(1-t[:,None])+self.support[hi]*t[:,None]
  side=np.max(p[:,:2]@self.N.T-supp,axis=1)
  return np.maximum.reduce([side,self.low-p[:,2],p[:,2]-self.high])*1000
 def front_rear(self,z):return (np.interp(z,self.z,-self.support[:,36]),np.interp(z,self.z,self.support[:,12]))
shell=Shell(target);donorshell=Shell(d['magazines']['AKM'])
H0=np.array(don['hand_in_mag']);basis0={n:rot(q) for n,q in don['finger_basis'].items()}
def pose(H,Q):
 p={'hand_l':H}
 for n in names[1:]:
  b=np.eye(4);b[:3,:3]=Q[n];p[n]=p[parents[n]]@local[n]@b
 skin=np.einsum('nvk,njk->nvj',bound,np.array([p[n] for n in names]))[:,:,:3]
 return p,np.sum(skin*weights.T[:,:,None],axis=0)
p0,v0=pose(H0,basis0)
controls=[];axes={};spread={};pads=[]
digits=['index','middle','ring','pinky','thumb']
for finger in digits:
 ns=[f'{finger}_{j:02}_l' for j in [1,2,3]]
 axis=unit(np.cross(p0[ns[1]][:3,3]-p0[ns[0]][:3,3],p0[ns[2]][:3,3]-p0[ns[1]][:3,3]))
 for n in ns:
  controls.append(n);axes[n]=p0[n][:3,:3].T@axis;spread[n]=unit(np.cross(np.array([0.,1.,0.]),axes[n]))
 for n in ns[1:]:
  ids=np.flatnonzero(labels==n);dist=donorshell.clearance(v0[ids]);sel=ids[np.argsort(dist)[:max(12,len(ids)//7)]];pads.append((finger,n,sel))
palm=np.flatnonzero((labels=='hand_l')&(v0[:,1]>.0)&(v0[:,1]<.046)&(v0[:,2]>-.015))
palm=palm[np.argsort(v0[palm,0])[:max(20,len(palm)//4)]]
if len(palm)<10:raise RuntimeError('Missing palmar support patch')
def posed(x):
 H=H0.copy();H[:3,:3]=R.from_rotvec(np.radians(x[3:6])).as_matrix()@H0[:3,:3];H[:3,3]+=x[:3]/1000
 Q={n:m.copy() for n,m in basis0.items()}
 for j,n in enumerate(controls):
  delta=axes[n]*math.radians(x[6+j])
  if '_01_' in n:
   delta+=spread[n]*math.radians(x[21+j//3])
   delta+=np.array([0.,1.,0.])*math.radians(x[26+j//3])
  Q[n]=Q[n]@R.from_rotvec(delta).as_matrix()
 p,v=pose(H,Q);return H,Q,p,v
def surface(v):return np.concatenate([v,v[edges].mean(1),v[faces].mean(1)])
def semantic(p,v):
 values=[]
 for finger,n,ids in pads:
  center=v[ids].mean(0);front,rear=shell.front_rear(center[2]);y=center[1]
  # The pads must stay on their own front/rear half, never wrap around the mouth.
  boundary=(front+rear)*.5
  values.extend([(y-boundary)*1000 if finger=='thumb' else (boundary-y)*1000,43-center[2]*1000,center[2]*1000+34])
 return np.array(values)
def objective(x):
 H,Q,p,v=posed(x);dist=shell.clearance(v);value=0.
 for finger,n,ids in pads:
  # Fixed donor pads, not the closest arbitrary vertex on each finger.
  dd=dist[ids];value+=np.mean((dd-1.)**2)*(.55 if '_02_' in n else 4.)
  c=v[ids].mean(0);front,rear=shell.front_rear(c[2])
  if finger=='thumb':value+=.3*((c[1]-rear-.002)*1000)**2
  else:value+=.14*((c[1]-front+.002)*1000)**2
 value+=6*np.mean((dist[palm]-1.4)**2)
 value+=.01*np.dot(x[:3],x[:3])+.025*np.dot(x[3:6],x[3:6])+.007*np.dot(x[6:21],x[6:21])+.06*np.dot(x[21:],x[21:])
 return float(value)
limits=[(-22,12),(-18,26),(-12,14)]+[(-20,20)]*3
for n in controls:
 limits.append((-30,30) if '_01_' in n else (-35,25) if '_02_' in n else (-20,25))
limits += [(-12,12)]*4+[(-25,25)]+[(-12,12)]*5
start=np.zeros(31);resumed=(O/'grasp_fit.json').exists()
if resumed:
 old=json.loads((O/'grasp_fit.json').read_text())['parameters'];start[:len(old)]=old
def penalty(x):
 p=posed(x);c=shell.clearance(surface(p[3]));wrong=np.minimum(semantic(p[2],p[3]),0)
 return objective(x)+120*np.mean(np.minimum(c-.55,0)**2)+12*min(0,c.min()-.55)**2+20*np.dot(wrong,wrong)
if not resumed:
 coarse=minimize(penalty,start,method='L-BFGS-B',bounds=limits,options={'maxiter':80,'maxfun':3000,'ftol':1e-6});start=coarse.x
 print('SVD_MAG_COARSE',coarse.fun,coarse.message,flush=True)
def constraint(x):
 H,Q,p,v=posed(x);return np.r_[shell.clearance(surface(v))-.45,semantic(p,v)]
solution=minimize(objective,start,method='SLSQP',bounds=limits,constraints=[{'type':'ineq','fun':constraint}],options={'maxiter':100,'ftol':.002})
H,Q,p,v=posed(solution.x)
# Opening retains front/rear opposition and the donor metacarpals; it does not
# interpolate all joints toward rig rest, which sweeps the thumb across the front.
opened={n:m.copy() for n,m in Q.items()}
for j,n in enumerate(controls):
 angle=-12 if '_01_' in n else -23 if '_02_' in n else -14
 opened[n]=opened[n]@R.from_rotvec(axes[n]*math.radians(angle)).as_matrix()
result={'donor':'RifleMagazineGrip20260922/IndexClearanceV4 AKM; V2 front/rear opposition',
 'hand_in_mag':H.tolist(),'finger_basis':{n:wxyz(q) for n,q in Q.items()},'open_basis':{n:wxyz(q) for n,q in opened.items()},
 'parameters':solution.x.tolist(),'objective':float(solution.fun),'optimizer_success':bool(solution.success),'optimizer_message':str(solution.message),
 'production_clearance_mm':float(shell.clearance(surface(v)).min()),'pad_regions':{n:ids.tolist() for _,n,ids in pads},
 'production_pad_means_mm':{n:float(shell.clearance(v[ids]).mean()) for _,n,ids in pads},'palm_mean_mm':float(shell.clearance(v[palm]).mean()),
 'method':'Fixed glove pad regions; front four fingers, rear thumb; continuous outer sections; complete surface clearance',
 'game_tested':False}
(O/'grasp_fit.json').write_text(json.dumps(result,indent=2))
print('SVD_MAG_GRASP_AUTHORED', {k:result[k] for k in ['objective','optimizer_success','optimizer_message','production_clearance_mm','production_pad_means_mm','palm_mean_mm']},flush=True)
