import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np,json
from pathlib import Path
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
O=Path(__file__).parent;D=np.load(O/'hand_lbs.npz');names=json.loads((O/'hand_lbs.json').read_text())['names'];idx={n:i for i,n in enumerate(names)}
rest=D['rest'];old=D['pose'];parents=D['parents'];weights=D['weights'];vertices=D['vertices'];fit=json.loads((O/'fit_baseline.json').read_text());G=np.array(fit['grip_matrix']);Gi=np.linalg.inv(G);profile=np.array(json.loads((O/'grip_profile.json').read_text()))
digits=['index','middle','ring','pinky'];left=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb','hand'))]
ids=np.flatnonzero(weights[:,left].sum(axis=1)>.7)[::1];w=weights[ids];v=vertices[ids]
active=np.flatnonzero(w.sum(axis=0)>0);pre=np.einsum('nb,bij,nj->bni',w[:,active],np.linalg.inv(rest[active]),v)
lr=np.array([np.linalg.inv(rest[p])@rest[i] if p>=0 else rest[i] for i,p in enumerate(parents)])
basis=np.array([np.linalg.inv(lr[i])@(np.linalg.inv(old[p])@old[i] if p>=0 else old[i]) for i,p in enumerate(parents)])
pivot=old[idx['middle_01_l'],:3,3];H0=old[idx['hand_l']]
groups=[np.flatnonzero(w[:,idx[f'{d}_{j:02}_l']]>.4) for d in digits for j in [1,2,3]]
groups+=[np.flatnonzero(w[:,idx['hand_l']]>.7),np.flatnonzero(w[:,idx['thumb_03_l']]>.4)]
def pose(x):
 p=old.copy();R=G[:3,:3]@Rotation.from_euler('xyz',x[3:6],degrees=True).as_matrix()@Gi[:3,:3];H=H0.copy();H[:3,:3]=R@H0[:3,:3];H[:3,3]=pivot+R@(H0[:3,3]-pivot)+G[:3,:3]@(x[:3]/1000);p[idx['hand_l']]=H
 for i in left:
  n=names[i]
  if n=='hand_l':continue
  b=basis[i].copy()
  if n.startswith(tuple(digits)) and '_metacarpal_' not in n:
   d,j=n.split('_')[:2];b[:3,:3]=Rotation.from_euler('z',x[6+digits.index(d)*3+int(j)-1],degrees=True).as_matrix()
  if '_metacarpal_' in n and n.split('_')[0] in digits:
   off=21+digits.index(n.split('_')[0])*2;b[:3,:3]=basis[i,:3,:3]@Rotation.from_euler('xz',x[off:off+2],degrees=True).as_matrix()
  if n=='thumb_01_l':b[:3,:3]=basis[i,:3,:3]@Rotation.from_euler('xyz',x[18:21],degrees=True).as_matrix()
  p[i]=p[parents[i]]@lr[i]@b
 return p
target=np.array([30,65,35]*4)
def residual(x):
 p=pose(x);points=np.einsum('bij,bnj->ni',p[active],pre)@Gi.T
 radius=np.interp(points[:,2],profile[:,0],profile[:,1]);sdf=np.linalg.norm(points[:,:2],axis=1)-radius
 sdf=np.maximum(sdf,np.maximum(-.1035-points[:,2],points[:,2]))
 penetration=np.minimum(sdf-.0011,0)*16000
 contacts=np.array([np.mean(np.sort(sdf[g])[:max(3,min(8,len(g)))])-.0008 for g in groups])*1800
 return np.r_[penetration,contacts,(x[6:18]-target)*.007,x[3:6]*.012,x[18:21]*.009,x[21:]*.03]
low=[-30,-40,-25,-30,-35,-35]+[0,35,15]*4+[-55]*3+[-18]*8
high=[60,40,25,30,35,35]+[80,95,65]*4+[55]*3+[18]*8

x=np.array(json.loads((O/'fist_solution.json').read_text())['parameters']);sol=least_squares(residual,x,bounds=(low,high),max_nfev=200,diff_step=.0003,ftol=1e-7,xtol=1e-7,gtol=1e-7);p=pose(sol.x)
(O/'fist_solution.json').write_text(json.dumps({'cost':float(np.sum(residual(sol.x)**2)),'parameters':sol.x.tolist(),'pose':{n:p[i].tolist() for i,n in enumerate(names)}},indent=2));print('FINAL',sol.cost,sol.nfev,flush=True)


