"""Fit sampled skinned pads, retaining native phalange lengths and skin weights."""
import numpy as np,json
from pathlib import Path
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;data=json.loads((O/'contact_bones.json').read_text());n=data['names'];ix={s:i for i,s in enumerate(n)}
z=np.load(O/'contact_inputs.npz');coords=z['coords'].astype(np.float64);initial=z['initial'].astype(np.float64);parents=data['parents']
indices=np.arange(0,coords.shape[1],3);coords=coords[:,indices]
def child(name,root):
 while name:
  if name==root:return True
  name=parents.get(name)
 return False
desc={s:[ix[a] for a in n if child(a,s)] for s in n}
params=[]
for digit in ('index','middle','ring','pinky'):
 for j in (1,2,3):params.append((digit+'_%02d_l'%j,np.array([0.,-1.,0.])))
for j in (1,2,3):
 for axis in ((0,1,0),(1,0,0)):params.append(('thumb_%02d_l'%j,np.array(axis,dtype=float)))
def poses(x):
 p=initial.copy();transport={s:np.eye(3) for s in n}
 for (s,axis),angle in zip(params,x[3:]):
  idx=ix[s];pivot=p[idx,:3,3].copy();rot=Rotation.from_rotvec(transport[s]@axis*angle).as_matrix()
  for k in desc[s]:
   p[k,:3,3]=rot@(p[k,:3,3]-pivot)+pivot;p[k,:3,:3]=rot@p[k,:3,:3];transport[n[k]]=rot@transport[n[k]]
 p[:,:3,3]+=x[:3]
 return p
def skin(p):return np.einsum('bij,bnj->ni',p[:,:3,:],coords)
def fields(v):
 # Main fore-end, barrel and tube. These cylinders conservatively contain
 # the scanned source shells in the grasp region; subsequent UE views use
 # the complete published geometry, not these fitting proxies.
 pump=np.sqrt(v[:,0]**2+(v[:,2]+.7594)**2)-.0226
 barrel=np.sqrt(v[:,0]**2+(v[:,2]+.7188)**2)-.0122
 return pump,barrel
base=skin(initial);bp,bb=fields(base)
dominant=np.argmax(coords[:,:,3],axis=0)
# Select inner pads near the fore-end, with contact below the barrel.
pads={}
for digit in ('index','middle','ring','pinky','thumb'):
 mask=np.array([n[i].startswith(digit+'_') and '_metacarpal_' not in n[i] for i in dominant])
 selected=np.flatnonzero(mask & (base[:,2]<-.739) & (bp<.008))
 if len(selected)<8:selected=np.flatnonzero(mask)[np.argsort(bp[mask])[:20]]
 pads[digit]=selected[::max(1,len(selected)//35)]
def residual(x):
 v=skin(poses(x));p,b=fields(v)
 res=[np.minimum(p-.0006,0)*800,np.minimum(b-.001,0)*900]
 for digit,ids in pads.items():res.append(np.maximum(p[ids]-.0015,0)*28)
 palm=dominant==ix['hand_l'];ids=np.flatnonzero(palm)[np.argsort(bp[palm])[:24]]
 res.append(np.maximum(p[ids]-.002,0)*35)
 res.extend([x[:3]*10,x[3:]*.018])
 # Maintain the thumb on the left and finger shafts on the right.
 thumb=np.array([n[i].startswith('thumb') for i in dominant]);finger=~thumb
 res.extend([np.maximum(v[thumb,0]+.019,0)*100,np.minimum(v[finger,0]+.004,0)*8])
 return np.concatenate(res)
x=np.zeros(3+len(params));lo=np.r_[[-.012,-.008,-.014],np.full(len(params),-.85)];hi=np.r_[[.014,.008,.009],np.full(len(params),.85)]
fit=least_squares(residual,x,bounds=(lo,hi),max_nfev=130,ftol=1e-7,xtol=1e-7,gtol=1e-7,diff_step=1e-4)
p=poses(fit.x);vp=skin(p);dp,db=fields(vp)
report={'grip':{s:p[i].tolist() for i,s in enumerate(n)},'translation':fit.x[:3].tolist(),'angles_degrees':np.degrees(fit.x[3:]).tolist(),'cost':float(fit.cost),'evaluations':fit.nfev,'minimum_pump_mm':float(dp.min()*1000),'minimum_barrel_mm':float(db.min()*1000),'before_pump_mm':float(bp.min()*1000),'before_barrel_mm':float(bb.min()*1000),'proxy_only':True}
(O/'optimized_grip.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='grip'})
