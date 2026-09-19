import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np,json
from pathlib import Path
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
O=Path(__file__).parent;D=np.load(O/'hand_lbs.npz');names=json.loads((O/'hand_lbs.json').read_text())['names'];idx={n:i for i,n in enumerate(names)}
rest=D['rest'];old=D['pose'];parents=D['parents'];weights=D['weights'];vertices=D['vertices'];fit=json.loads((O/'fit_baseline.json').read_text());G=np.array(json.loads((O/'body_frame.json').read_text()));Gi=np.linalg.inv(G);profile=np.array(json.loads((O/'grip_profile.json').read_text()))
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
  if n in ['thumb_02_l','thumb_03_l']:
   off=29+(int(n.split('_')[1])-2)*3;b[:3,:3]=basis[i,:3,:3]@Rotation.from_euler('xyz',x[off:off+3],degrees=True).as_matrix()
  p[i]=p[parents[i]]@lr[i]@b
 return p

# Keep the accepted direction; tighten contact patches instead of chasing a single fingertip.
x0=np.zeros(35)
for k,d in enumerate(digits):
 for j in range(1,4):x0[6+k*3+j-1]=Rotation.from_matrix(basis[idx[f'{d}_{j:02}_l'],:3,:3]).as_euler('xyz',degrees=True)[2]
initial=np.einsum('bij,bnj->ni',old[active],pre)@Gi.T
knuckles=np.mean([old[idx[d+'_01_l'],:3,3] for d in digits],axis=0);pc=.65*knuckles+.35*old[idx['hand_l'],:3,3];pc=(Gi@np.r_[pc,1])[:3]
palm_ids=np.flatnonzero(w[:,idx['hand_l']]>.5);near=palm_ids[np.argsort(np.linalg.norm(initial[palm_ids,:3]-pc,axis=1))[:90]];groups[-2]=near
strength=np.array([1.3,1.8,1.2]*4+[6,6])
mapping=np.full(len(vertices),-1);mapping[ids]=np.arange(len(ids));faces=mapping[np.load(O/'triangles.npy')];faces=faces[np.all(faces>=0,axis=1)]
def distances(p):
 points=np.einsum('bij,bnj->ni',p[active],pre)@Gi.T;corners=points[faces];points=np.concatenate([points,corners.mean(axis=1),(corners[:,0]+corners[:,1])*.5,(corners[:,1]+corners[:,2])*.5,(corners[:,2]+corners[:,0])*.5]);radius=np.interp(points[:,2],profile[:,0],profile[:,1]);sdf=np.linalg.norm(points[:,:2],axis=1)-radius
 return np.maximum(sdf,np.maximum(-.1035-points[:,2],points[:,2]+.022))
def contacts(sdf):return np.array([np.mean(np.sort(sdf[g])[:min(20,len(g))]) for g in groups])
def residual(x):
 sdf=distances(pose(x));penetration=np.minimum(sdf-.00075,0)*16000;contact=(contacts(sdf)-.00055)*strength*2200
 return np.r_[penetration,contact,(x[6:18]-x0[6:18])*.015,x[:3]*.03,x[3:6]*.08,x[18:21]*.025,x[21:29]*.06,x[29:]*.06]


base=json.loads((O.parent/'FirmGrip/fist_solution.json').read_text());candidate=json.loads((O/'fist_solution.json').read_text());x=np.array(base['parameters'])+.7*(np.array(candidate['parameters'])-np.array(base['parameters']));p=pose(x);candidate['parameters']=x.tolist();candidate['pose']={n:p[i].tolist() for i,n in enumerate(names)};candidate['collision_refinement_fraction']=.7;candidate['after_patch_distance_mm']=(contacts(distances(p))*1000).tolist();(O/'fist_solution.json').write_text(json.dumps(candidate,indent=2))
