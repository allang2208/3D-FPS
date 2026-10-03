"""Fit a closed thumb/finger grasp to the actual SVD knob without finger translations."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
O=Path(__file__).parent;d=json.loads((O/'inputs.json').read_text())
rest={n:np.array(m) for n,m in d['rest'].items()};parents=d['parents'];idle={n:np.array(m) for n,m in d['poses'][0].items()}
local={n:np.linalg.inv(rest[parents[n]])@m for n,m in rest.items() if parents[n]}
names=[n for n in rest if n=='hand_r' or n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
skin=d['skin'];use=[i for i,w in enumerate(skin['weights']) if sum(w.get(n,0) for n in names)/max(1e-8,sum(w.values()))>.985]
vv=np.c_[[skin['vertices'][i] for i in use],np.ones(len(use))];weights=np.array([[skin['weights'][i].get(n,0) for n in names] for i in use]);weights/=weights.sum(1)[:,None]
bound={n:vv@np.linalg.inv(rest[n]).T for n in names};active={n:np.flatnonzero(weights[:,i]>0) for i,n in enumerate(names)};labels=np.array(names)[weights.argmax(1)]
Q0={n:(np.linalg.inv(local[n])@np.linalg.inv(idle[parents[n]])@idle[n])[:3,:3] for n in names if n!='hand_r'}
H0=np.array(json.loads((O.parent/'SVDChargeGrip20260924/contact_fit.json').read_text())['contact_hand_root'])
knob=np.array(d['parts']['SM_SVD_ChargingHandle']['vertices']);eq=np.unique(np.round(ConvexHull(knob).equations,7),axis=0)
center=(knob.min(0)+knob.max(0))/2
def posed(H,Q):
 p={'hand_r':H};v=np.zeros((len(vv),3))
 for i,n in enumerate(names):
  if n!='hand_r':
   b=np.eye(4);b[:3,:3]=Q[n];p[n]=p[parents[n]]@local[n]@b
  ids=active[n];v[ids]+=(bound[n][ids]@p[n].T)[:,:3]*weights[ids,i,None]
 return p,v
p0,v0=posed(H0,Q0);axes={};controls=[]
for digit in ['index','middle','ring','pinky','thumb']:
 ns=[f'{digit}_{j:02}_r' for j in [1,2,3]];a=p0[ns[1]][:3,3]-p0[ns[0]][:3,3];b=p0[ns[2]][:3,3]-p0[ns[1]][:3,3]
 axis=np.cross(a,b);axis/=max(np.linalg.norm(axis),1e-8)
 for n in ns:axes[n]=p0[n][:3,:3].T@axis;controls.append(n)
patches={digit:np.flatnonzero(np.isin(labels,[digit+'_02_r',digit+'_03_r'])) for digit in ['index','middle','thumb']}
# Thumb pads oppose two curled fingers on the short tab; ring/little fingers
# stay closed against the palm instead of being forced onto a 22 mm handle.
targets={'index':center+np.array([-.003,-.007,-.002]),'middle':center+np.array([-.025,-.011,-.004]),'thumb':center+np.array([-.002,.001,.004])}
def make(x):
 H=H0.copy();H[:3,3]+=x[:3]/1000;H[:3,:3]=R.from_rotvec(np.radians(x[3:6])).as_matrix()@H0[:3,:3]
 Q={n:q.copy() for n,q in Q0.items()}
 for n,angle in zip(controls,x[6:21]):Q[n]=Q[n]@R.from_rotvec(axes[n]*math.radians(angle)).as_matrix()
 Q['thumb_01_r']=Q['thumb_01_r']@R.from_euler('yz',x[21:23],degrees=True).as_matrix()
 p,v=posed(H,Q);return H,Q,p,v
def cost(x):
 H,Q,p,v=make(x);dist=(v@eq[:,:3].T+eq[:,3]).max(1)*1000;inside=np.minimum(dist+.2,0)
 loss=12*np.mean(inside**2)+4*min(inside)**2
 for digit,ids in patches.items():
  dif=np.linalg.norm((v[ids]-targets[digit])*1000,axis=1);near=np.sort(dif)[:8];loss+=(.7 if digit=='middle' else 5)*np.mean(near**2)
 # Keep the hand outside the receiver side near the knob, while allowing
 # pads to wrap around the protruding tab.
 box=(np.abs(v[:,1]-center[1])<.07)&(v[:,2]>center[2]-.055)&(v[:,2]<center[2]+.055)
 pen=np.maximum((v[box,0]+.015)*1000,0);loss+=8*np.mean(pen**2) if len(pen) else 0
 # Preserve a compact grasp: no metacarpal edits, no finger fan/axial twist.
 loss+=.005*np.dot(x[:3],x[:3])+.010*np.dot(x[3:6],x[3:6])+.035*np.dot(x[6:],x[6:])
 return float(loss)
bounds=[(-90,35),(-90,50),(-35,100)]+[(-150,150)]*3
for n in controls:
 bounds.append((-10,25) if n=='index_03_r' else (-20,65) if n.startswith('index') else (-20,32) if n.startswith('thumb') else (-10,20))
bounds += [(-35,35),(-30,30)]
seed=json.loads((O/'grasp_fit.json').read_text())['parameters_mm_deg'] if (O/'grasp_fit.json').exists() else [0.]*21
x=np.array(seed[:21]+[0.,0.]);x=np.clip(x,np.array(bounds)[:,0],np.array(bounds)[:,1])
coarse=minimize(lambda v:cost(np.r_[v,x[6:]]),x[:6],method='Powell',bounds=bounds[:6],options={'maxiter':35,'xtol':.02,'ftol':.0002});x[:6]=coarse.x
fit=minimize(cost,x,method='L-BFGS-B',bounds=bounds,options={'maxiter':220,'maxfun':8000,'ftol':1e-9});H,Q,p,v=make(fit.x)
def quat(m):
 q=R.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
report={'hand_in_root':H.tolist(),'finger_basis':{n:quat(q) for n,q in Q.items()},'controls':controls,'parameters_mm_deg':fit.x.tolist(),
 'pad_target_root':{k:v.tolist() for k,v in targets.items()},'pad_distance_mm':{k:float(np.sort(np.linalg.norm((v[ids]-targets[k])*1000,axis=1))[:8].mean()) for k,ids in patches.items()},
 'objective':float(fit.fun),'optimizer_message':str(fit.message),'method':'Closed grip from the right hand: thumb opposition to index and middle; ring and little fingers retain a compact fist; only anatomical flexion and rigid palm fit.'}
(O/'grasp_fit.json').write_text(json.dumps(report,indent=2));print('SVD_GRASP_FIT',json.dumps({k:v for k,v in report.items() if k not in ['hand_in_root','finger_basis']}),flush=True)
