"""Fit the SVD right palm and bounded finger flexion to its retained rear grip."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
O=Path(__file__).parent;d=json.loads((O/'grip_inputs.json').read_text())
rest={n:np.array(m) for n,m in d['rest'].items()};idle={n:np.array(m) for n,m in d['idle'].items()};parents=d['parents']
local={n:np.linalg.inv(rest[parents[n]])@m for n,m in rest.items() if parents[n]}
skin=d['skin'];names=skin['names'];vv=np.c_[skin['vertices'],np.ones(len(skin['vertices']))]
weights=np.array([[w.get(n,0) for n in names] for w in skin['weights']]);weights/=weights.sum(1)[:,None]
bound={n:vv@np.linalg.inv(rest[n]).T for n in names};active={n:np.flatnonzero(weights[:,i]>0) for i,n in enumerate(names)}
labels=np.array([names[i] for i in weights.argmax(1)])
H0=np.linalg.inv(idle['WPN_root'])@idle['hand_r']
Q0={n:(np.linalg.inv(local[n])@np.linalg.inv(idle[parents[n]])@idle[n])[:3,:3] for n in names if n!='hand_r'}
grip=np.array(d['target']['SM_SVD_RetainedGrip']['vertices']);hull=ConvexHull(grip);eq=np.unique(np.round(hull.equations,7),axis=0)
def distance(v):return np.max(v@eq[:,:3].T+eq[:,3],axis=1)*1000
def posed(H,Q):
 p={'hand_r':H};out=np.zeros((len(vv),3))
 for i,n in enumerate(names):
  if n!='hand_r':
   b=np.eye(4);b[:3,:3]=Q[n];p[n]=p[parents[n]]@local[n]@b
  ids=active[n];out[ids]+=(bound[n][ids]@p[n].T)[:,:3]*weights[ids,i,None]
 return p,out
p0,v0=posed(H0,Q0);axes={};controls=[]
# Keep the trigger finger and metacarpal frames. The other three fingers and
# thumb close around the grip using their existing anatomical bending planes.
for digit in ['middle','ring','pinky','thumb']:
 ns=[f'{digit}_{j:02}_r' for j in [1,2,3]];a=p0[ns[1]][:3,3]-p0[ns[0]][:3,3];b=p0[ns[2]][:3,3]-p0[ns[1]][:3,3]
 axis=np.cross(a,b);axis=axis/np.linalg.norm(axis) if np.linalg.norm(axis)>1e-7 else p0[ns[1]][:3,2]
 for n in ns:axes[n]=p0[n][:3,:3].T@axis;controls.append(n)
palm=np.flatnonzero(labels=='hand_r');patches={digit:np.flatnonzero(np.isin(labels,[digit+'_02_r',digit+'_03_r'])) for digit in ['middle','ring','pinky','thumb']}
def make(x):
 H=H0.copy();H[:3,3]+=x[:3]/1000;H[:3,:3]=R.from_rotvec(np.radians(x[3:6])).as_matrix()@H0[:3,:3]
 Q={n:m.copy() for n,m in Q0.items()}
 for n,angle in zip(controls,x[6:]):Q[n]=Q[n]@R.from_rotvec(axes[n]*math.radians(angle)).as_matrix()
 p,v=posed(H,Q);return H,Q,p,v
def cost(x):
 H,Q,p,v=make(x);dist=distance(v);inside=np.minimum(dist+.35,0)
 value=30*np.mean(inside*inside)+3*min(inside)**2
 for ids in patches.values():
  near=np.sort(dist[ids])[:max(12,len(ids)//12)];value+=2.5*(near.mean()-.7)**2
 near=np.sort(dist[palm])[:max(12,len(palm)//18)];value+=2.2*(near.mean()-1.0)**2
 # The palm belongs to the lower retained grip, not the tang/end plate.
 centers=np.array([p[n][:3,3] for n in ['middle_01_r','ring_01_r','pinky_01_r']])
 value+=15000*np.sum(np.maximum(centers[:,2]+.008,0)**2)
 value+=.008*np.dot(x[:3],x[:3])+.03*np.dot(x[3:6],x[3:6])+.055*np.dot(x[6:],x[6:])
 return float(value)
bounds=[(-25,25),(-25,25),(-8,36)]+[(-18,18)]*3
for n in controls:bounds.append((-10,10) if n.startswith('thumb') else (-8,24) if '_01_' in n else (-10,20) if '_02_' in n else (-5,12))
x=np.r_[0.,0.,20.,np.zeros(15)]
coarse=minimize(lambda v:cost(np.r_[v,x[6:]]),x[:6],method='Powell',bounds=bounds[:6],options={'maxiter':22,'xtol':.03,'ftol':.001});x[:6]=coarse.x
fit=minimize(cost,x,method='L-BFGS-B',bounds=bounds,options={'maxiter':120,'maxfun':4500,'ftol':1e-8})
H,Q,p,v=make(fit.x)
def quat(m):
 q=R.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
report={'hand_in_root':H.tolist(),'finger_basis':{n:quat(q) for n,q in Q.items()},'parameters_mm_deg':fit.x.tolist(),'controls':controls,
 'method':'current retained SVD rear grip; fixed metacarpals and trigger finger, bounded anatomical flexion; no finger translations',
 'before_contact_mm':{k:float(np.sort(distance(v0[ids]))[:max(12,len(ids)//12)].mean()) for k,ids in patches.items()},
 'after_contact_mm':{k:float(np.sort(distance(v[ids]))[:max(12,len(ids)//12)].mean()) for k,ids in patches.items()},
 'objective':float(fit.fun),'optimizer_message':str(fit.message),'game_tested':False}
(O/'rear_grip.json').write_text(json.dumps(report,indent=2));print('SVD_REAR_GRIP_FIT',json.dumps({k:v for k,v in report.items() if k not in ['hand_in_root','finger_basis']}),flush=True)
