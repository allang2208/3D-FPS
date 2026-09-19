import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np,json
from pathlib import Path
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
O=Path(__file__).parent;OLD=O.parent/'CantedForegrip20260911/ThumbClose';D=np.load(OLD/'hand_lbs.npz');names=json.loads((OLD/'hand_lbs.json').read_text())['names'];idx={n:i for i,n in enumerate(names)};parents=D['parents'];rest=D['rest'];fit=json.loads((OLD/'fit_final.json').read_text());vf=json.loads((O.parent/'VerticalGripErgonomic20260911/vertical/fit_final.json').read_text());old=np.array([fit['old'][n] for n in names]);G=np.array(fit['grip_matrix']);B=np.array(json.loads((OLD/'body_frame.json').read_text()));Bi=np.linalg.inv(B);Gi=np.linalg.inv(G);root=old[idx['WPN_root']];H0=root@np.array(fit['hand_in_root']);H0i=np.linalg.inv(H0);lr=np.array([np.linalg.inv(rest[p])@rest[i] if p>=0 else rest[i] for i,p in enumerate(parents)]);left=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))];weights=D['weights'];selected=np.flatnonzero(weights[:,[idx['hand_l']]+left].sum(axis=1)>.6)[::4];w=weights[selected];active=np.flatnonzero(w.sum(axis=0)>0);pre=np.einsum('nb,bij,nj->bni',w[:,active],np.linalg.inv(rest[active]),D['vertices'][selected]);digits=['index','middle','ring','pinky'];all_digits=digits+['thumb'];di={d:np.flatnonzero(w[:,[i for i,n in enumerate(names) if n.startswith(d+'_') and n.endswith('_l')]].sum(axis=1)>.9) for d in all_digits};seg={d:[np.flatnonzero(w[:,idx[f'{d}_{j:02}_l']]>.5) for j in [1,2,3]] for d in all_digits};palm=np.flatnonzero(w[:,idx['hand_l']]>.8);profile=np.array(json.loads((OLD/'grip_profile.json').read_text()));profile=profile[profile[:,0]<-.024]
def sdf(points):
 b=(np.c_[points,np.ones(len(points))]@Bi.T)[:,:3];rad=np.linalg.norm(b[:,:2],axis=1)-np.interp(b[:,2],profile[:,0],profile[:,1]);shaft=np.maximum(rad,np.maximum(-.1035-b[:,2],b[:,2]+.024));ball=np.maximum(np.linalg.norm(b-np.array([0,0,-.014]),axis=1)-.021,b[:,2]+.002);g=(np.c_[points,np.ones(len(points))]@Gi.T)[:,:3];q=np.abs(g-np.array([0,0,-.00675]))-np.array([.018,.0165,.00675]);box=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.max(q,axis=1),0);return np.minimum(np.minimum(shaft,ball),box)
def pose(x):
 p=old.copy();p[idx['hand_l']]=H0.copy();p[idx['hand_l'],:3,3]+=B[:3,:3]@(x[:3]/1000);p[idx['hand_l'],:3,:3]=B[:3,:3]@R.from_euler('xyz',x[3:6],degrees=True).as_matrix()@Bi[:3,:3]@H0[:3,:3]
 for i in left:
  n=names[i];b=np.array(vf['basis'][n]);k=next((j for j,d in enumerate(digits) if n.startswith(d+'_')),None)
  if k is not None:
   fan,mcp,pip,dip=x[6+k*4:10+k*4]
   if 'metacarpal' in n:b[:3,:3]=b[:3,:3]@R.from_euler('y',fan,degrees=True).as_matrix()
   else:
    j=int(n.split('_')[1]);angle=mcp if j==1 else pip if j==2 else pip*.62+dip;b[:3,:3]=b[:3,:3]@R.from_euler('z',angle,degrees=True).as_matrix()
  p[i]=p[parents[i]]@lr[i]@b
 return p
row=H0[:3,:3]@np.array([0,0,1.]);p0=pose(np.zeros(22));row=(p0[idx['index_01_l'],:3,3]-p0[idx['pinky_01_l'],:3,3]);row/=np.linalg.norm(row)
def fun(x):
 p=np.einsum('bij,bnj->ni',pose(x)[active],pre)[:,:3];sd=sdf(p);out=[np.minimum(sd-.0008,0)*5000]
 for d in digits:
  for ids in seg[d]:out.append(np.array([(np.sort(sd[ids])[:4].mean()-.001)*700]))
 for ids in [palm,seg['thumb'][2]]:out.append(np.array([(np.sort(sd[ids])[:4].mean()-.001)*300]))
 for a,b in zip(digits,digits[1:]):
  gap=(p[di[a]]@row).min()-(p[di[b]]@row).max();out.append(np.array([min(gap-.0005,0)*3000]))
 out.extend([x[:3]*.03,x[3:6]*.07,x[6:]*.02]);return np.concatenate(out)
lo=np.array([-30,-30,-25]+[-18]*3+[-10,-40,-35,-10]*4,float);hi=np.array([30,30,25]+[18]*3+[10,40,25,10]*4,float);best=None
for attempt in range(2):
 x=np.zeros(22) if best is None else best.x.copy();r=least_squares(fun,x,bounds=(lo,hi),max_nfev=240,diff_step=.004,ftol=1e-5,xtol=1e-5,gtol=1e-5)
 if best is None or np.linalg.norm(r.fun)<np.linalg.norm(best.fun):best=r
 print('NATURAL_FIT',attempt,np.linalg.norm(best.fun),best.x.tolist(),flush=True)
 (O/'natural_solution.json').write_text(json.dumps({'parameters':best.x.tolist(),'pose':{n:pose(best.x)[i].tolist() for i,n in enumerate(names)}},indent=2))
