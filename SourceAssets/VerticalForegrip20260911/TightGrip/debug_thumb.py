from pathlib import Path
O=Path(__file__).parent
exec((O/'solve_fist.py').read_text().split('target=np.array')[0])
from scipy.interpolate import CubicSpline
fit=json.loads((O/'fit_final.json').read_text());entries=json.loads((O/'release_profile.json').read_text());ts=np.array([e['u'] for e in entries]);smooth=lambda x:np.clip(x,0,1)**2*(3-2*np.clip(x,0,1))
p0=pose(np.array(json.loads((O/'fist_solution.json').read_text())['parameters']))
thumb=[idx[f'thumb_{j:02}_l'] for j in [1,2,3]]
ids=np.flatnonzero(weights[:,thumb].sum(axis=1)>.15);w=weights[ids];v=vertices[ids];active=np.flatnonzero(w.sum(axis=0)>0);pre=np.einsum('nb,bij,nj->bni',w[:,active],np.linalg.inv(rest[active]),v)
base=np.array([np.linalg.inv(lr[i])@(np.linalg.inv(p0[p])@p0[i] if p>=0 else p0[i]) for i,p in enumerate(parents)])
P=np.repeat(p0[None],len(ts),axis=0)
for k,t in enumerate(ts):
 P[k,idx['hand_l'],:3,3]+=G[:3,:3]@np.array(fit['release_vector'])*smooth(t)
 for i in left:
  n=names[i]
  if n=='hand_l':continue
  b=base[i].copy()
  if n.startswith(tuple(digits)) and any(s in n for s in ['_01_','_02_','_03_']):b[:3,:3]=Rotation.from_rotvec(Rotation.from_matrix(b[:3,:3]).as_rotvec()*(1-smooth(t*1.5))).as_matrix()
  P[k,i]=P[k,parents[i]]@lr[i]@b

def trajectory(x):return CubicSpline([0,.2,.4,.65,1],np.vstack([np.zeros(3),x.reshape(3,3),np.zeros(3)]),bc_type='clamped')(ts)
def calc(x):
 angles=trajectory(x);p=P.copy();b=np.repeat(base[thumb[0]][None],len(ts),axis=0);b[:,:3,:3]=b[:,:3,:3]@Rotation.from_euler('xyz',angles,degrees=True).as_matrix();p[:,thumb[0]]=p[:,parents[thumb[0]]]@lr[thumb[0]]@b
 for i in thumb[1:]:p[:,i]=p[:,parents[i]]@lr[i]@base[i]
 points=np.einsum('kbij,bnj->kni',p[:,active],pre)@Gi.T
 sdf=np.linalg.norm(points[:,:,:2],axis=2)-np.interp(points[:,:,2],profile[:,0],profile[:,1]);sdf=np.maximum(sdf,np.maximum(-.138-points[:,:,2],points[:,:,2]))
 return angles,sdf

def residual(x):
 a,s=calc(x);return np.r_[np.minimum(s-.001,0).ravel()*20000,x*.025,np.diff(a,n=2,axis=0).ravel()*.4]

a,s=calc(np.zeros(9));print([(round(t,2),round(float(row.min())*1000,2)) for t,row in zip(ts,s)])
