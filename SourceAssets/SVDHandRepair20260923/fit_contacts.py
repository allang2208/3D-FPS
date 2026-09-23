"""Bounded production fitting of complete donor hands to SVD interfaces.
No individual finger translations, metacarpal rotations, rest, scale or skin edits.
"""
import json,math,sys,numpy as np
from pathlib import Path
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
O=Path(__file__).parent;d=json.loads((O/'inputs.json').read_text());rest={n:np.array(v) for n,v in d['rest'].items()};parents=d['parents'];idle={n:np.array(v) for n,v in d['idle'].items()}
local={n:np.linalg.inv(rest[parents[n]])@m for n,m in rest.items() if parents[n]};out=json.loads((O/'contacts.json').read_text()) if (O/'contacts.json').exists() else {}
def rotation(q):return R.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
def quat(m):
 q=R.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
def hull(v):
 h=ConvexHull(np.unique(np.round(v,7),axis=0));eq=np.unique(np.round(h.equations,7),axis=0)
 def distance(p):return np.max(p@eq[:,:3].T+eq[:,3],axis=1)*1000
 return distance
def solve(kind,side,H,basis,target,obstacle=None):
 if len(sys.argv)>1 and kind not in sys.argv[1:]:return
 skin=d['skin'][side];names=skin['names'];vv=np.c_[skin['vertices'],np.ones(len(skin['vertices']))];weights=np.array([[w.get(n,0) for n in names] for w in skin['weights']]);weights/=weights.sum(1)[:,None]
 bound={n:vv@np.linalg.inv(rest[n]).T for n in names};labels=np.array([names[i] for i in weights.argmax(1)]);q0={n:rotation(basis[n]) for n in names if n!='hand_'+side}
 dist=hull(target);obdist=hull(obstacle) if obstacle is not None else None
 def posed(hand,rotations):
  p={'hand_'+side:hand};result=np.zeros((len(vv),3))
  for n in names:
   if n not in p:
    b=np.eye(4);b[:3,:3]=rotations[n];p[n]=p[parents[n]]@local[n]@b
   i=names.index(n);result+=(bound[n]@p[n].T)[:,:3]*weights[:,i,None]
  return p,result
 p0,s0=posed(H,q0);axes={};controls=[]
 if kind!='hook':
  for finger in ['index','middle','ring','pinky','thumb']:
   n1,n2,n3=[f'{finger}_{j:02}_{side}' for j in [1,2,3]];v1=p0[n2][:3,3]-p0[n1][:3,3];v2=p0[n3][:3,3]-p0[n2][:3,3];axis=np.cross(v1,v2)
   if np.linalg.norm(axis)<1e-6:axis=p0[n2][:3,2]
   axis/=np.linalg.norm(axis)
   for n in [n1,n2,n3]:axes[n]=p0[n][:3,:3].T@axis;controls.append(n)
 contact=[]
 for f in (['index'] if kind=='hook' else ['thumb','index','middle','ring','pinky']):
  contact.append(np.flatnonzero(np.isin(labels,[f+'_02_'+side,f+'_03_'+side])))
 palm=np.flatnonzero(labels=='hand_'+side)
 faces=np.array([[f[0],f[i],f[i+1]] for f in skin['faces'] for i in range(1,len(f)-1)])
 def make(x):
  h=H.copy();h[:3,:3]=R.from_rotvec(np.radians(x[3:6])).as_matrix()@H[:3,:3];h[:3,3]+=np.array(x[:3])/1000
  qr={n:m.copy() for n,m in q0.items()}
  for n,a in zip(controls,x[6:]):qr[n]=qr[n]@R.from_rotvec(axes[n]*math.radians(a)).as_matrix()
  p,v=posed(h,qr);return h,qr,p,v
 def cost(x):
  h,qr,p,v=make(x);clear=dist(v);pts=np.concatenate([v,v[faces].mean(1)])
  intrusion=np.minimum(dist(pts)-.25,0);value=40*np.mean(intrusion**2)+4*np.min(intrusion)**2
  for ids in contact:
   patch=np.sort(clear[ids])[:max(8,len(ids)//16)];value+=3*(patch.mean()-1.0)**2
  if kind!='hook':
   patch=np.sort(clear[palm])[:12];value+=.8*(patch.mean()-2.5)**2
  if obdist is not None:
   z=np.minimum(obdist(pts)-.4,0);value+=80*np.mean(z*z)+8*min(z)**2
  value+=.014*np.dot(x[:3],x[:3])+.02*np.dot(x[3:6],x[3:6])+.025*np.dot(x[6:],x[6:])
  return float(value)
 limits=[(-22,22),(-15,15),(-22,22)]+[(-25,25)]*3
 if kind=='magazine':limits=[(-65,35),(-70,40),(-40,40)]+[(-35,35)]*3
 if kind=='hook':limits=[(-18,8),(-12,12),(-12,15)]+[(-15,15)]*3
 for n in controls:
  limit=((-12,12) if n.startswith('thumb') else (-20,50) if '_01_' in n and kind=='guard' else (-15,25) if '_02_' in n else (-15,18))
  limits.append(limit)
 # Whole-hand registration first; restricted local flex follows the donor's own axes.
 start=np.array(out[kind]['parameters_mm_deg']) if kind in out else np.zeros(len(limits));coarse=minimize(lambda z:cost(np.r_[z,start[6:]]),start[:6],method='Powell',bounds=limits[:6],options={'maxiter':18,'xtol':.04,'ftol':.002});start[:6]=coarse.x
 result=minimize(cost,start,method='L-BFGS-B',bounds=limits,options={'maxiter':125,'maxfun':5000,'ftol':1e-7,'finite_diff_rel_step':1e-4})
 h,qr,p,v=make(result.x);out[kind]={'hand':[list(row) for row in h],'finger_basis':{n:quat(m) for n,m in qr.items()},'parameters_mm_deg':result.x.tolist(),'controls':controls,'objective':float(result.fun),'optimization_message':str(result.message),'method':'grouped donor, semantic multi-pad and palm fit with conservative shell avoidance; no finger translation'}
 out[kind]['fitting_residuals_mm']={'minimum_shell_clearance':float(dist(v).min()),'palm_near_patch':float(np.mean(np.sort(dist(v[palm]))[:12])),'finger_near_patches':[float(np.mean(np.sort(dist(v[ids]))[:max(8,len(ids)//16)])) for ids in contact]}
 (O/'contacts.json').write_text(json.dumps(out,indent=2));print('SVD_REPAIR_FITTED',kind,result.fun,str(result.message),flush=True)
body=np.array(d['targets']['Body']['vertices']);guard=body[(body[:,1]>-.46)&(body[:,1]<-.235)&(body[:,2]<.074)]
H=np.linalg.inv(idle['WPN_root'])@idle['hand_l'];solve('guard','l',H,d['idle_fingers'],guard)
don=d['donor'];mag=np.array(d['targets']['Magazine']['vertices']);old=np.array(don['magazine']['vertices']);H=np.array(don['hand_in_mag']);H[:3,3]+=(mag.min(0)+mag.max(0)-old.min(0)-old.max(0))*.5
solve('magazine','l',H,don['finger_basis'],mag)
# The hook uses the accepted ASH12/A762 grouped shape, not independently fitted fingertips.
hook=d['hook'];near=body[(body[:,1]>-.235)&(body[:,1]<.0)&(body[:,2]>.006)&(body[:,2]<.08)]
solve('hook','r',np.array(hook['hand_in_root']),hook['finger_basis'],np.array(d['targets']['ChargingHandle']['vertices']),near)
