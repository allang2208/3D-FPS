"""Limited planar finger fit. Does not change joint positions, lengths or scale."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np,json,sys
from pathlib import Path
from scipy.spatial.transform import Rotation as R
from scipy.spatial import cKDTree,ConvexHull
from scipy.optimize import least_squares
O=Path(__file__).parent
for variant in sys.argv[1:] or ['vertical','prism']:
 d=O/variant;D=np.load(d/'lbs.npz');names=json.loads((d/'lbs.json').read_text())['names'];idx={n:i for i,n in enumerate(names)};rest=D['rest'];old=D['pose'];parents=D['parents'];weights=D['weights'];vertices=D['vertices'];gd=np.load(d/'grip.npz');G=gd['G'];Gi=np.linalg.inv(G)
 digits=['index','middle','ring','pinky'];all_digits=digits+['thumb'];left=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(tuple(all_digits+['hand']))]
 selected=np.flatnonzero(weights[:,left].sum(axis=1)>.75)[::3];w=weights[selected];v=vertices[selected];active=np.flatnonzero(w.sum(axis=0)>0);pre=np.einsum('nb,bij,nj->bni',w[:,active],np.linalg.inv(rest[active]),v)
 lr=np.array([np.linalg.inv(rest[p])@rest[i] if p>=0 else rest[i] for i,p in enumerate(parents)]);basis=np.array([np.linalg.inv(lr[i])@(np.linalg.inv(old[p])@old[i] if p>=0 else old[i]) for i,p in enumerate(parents)])
 segids={digit:[np.flatnonzero(w[:,idx[f'{digit}_{j:02}_l']]>.5) for j in [1,2,3]] for digit in all_digits};digitids={digit:np.flatnonzero(w[:,[idx[n] for n in names if n.startswith(digit+'_') and n.endswith('_l')]].sum(axis=1)>.9) for digit in all_digits}
 palmids=np.flatnonzero(w[:,idx['hand_l']]>.8)
 gv=gd['vertices'];tri=gv[gd['faces']];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
 # Dense triangle samples retain actual mount, shaft taper and short prism outline.
 points=[];normals=[]
 for u,t in [(1/3,1/3),(.1,.1),(.8,.1),(.1,.8),(.5,.1),(.1,.5),(.4,.4)]:points.append(tri[:,0]*(1-u-t)+tri[:,1]*u+tri[:,2]*t);normals.append(normal)
 points=np.concatenate(points);normals=np.concatenate(normals);tree=cKDTree(points)
 zz=np.unique(np.round(gv[:,2],5));profile=np.array([(z,np.linalg.norm(gv[abs(gv[:,2]-z)<.00001,:2],axis=1).max()) for z in zz if z<-.014])
 hull=ConvexHull(gv);planes=hull.equations
 def sdf(x):
  if variant=='vertical':
   radial=np.linalg.norm(x[:,:2],axis=1)-np.interp(x[:,2],profile[:,0],profile[:,1])
   body=np.maximum(radial,np.maximum(-.1035-x[:,2],x[:,2]+.014))
   box=np.abs(x-np.array([0,0,-.00675]))-np.array([.018,.0165,.00675]);box=np.linalg.norm(np.maximum(box,0),axis=1)+np.minimum(np.max(box,axis=1),0)
   return np.minimum(body,box)
  return (x@planes[:,:3].T+planes[:,3]).max(axis=1)
 def pose(x):
  p=old.copy();p[idx['hand_l'],:3,3]+=G[:3,:3]@(x[:3]/1000)
  for i in left:
   n=names[i]
   if n=='hand_l':continue
   b=basis[i].copy()
   if n.startswith(tuple(digits)):
    digit=n.split('_')[0];k=digits.index(digit);fan,flex,pip,dip=x[3+4*k:7+4*k]
    if 'metacarpal' in n:
     m=p[parents[i]]@lr[i]@b;rot=G[:3,:3]@R.from_euler('y',fan,degrees=True).as_matrix()@Gi[:3,:3];m[:3,:3]=rot@m[:3,:3];p[i]=m;continue
    j=int(n.split('_')[1])
    if j==1:
     m=p[parents[i]]@lr[i]@b;m[:3,:3]=old[i,:3,:3]@R.from_euler('z',flex,degrees=True).as_matrix();p[i]=m;continue
    b[:3,:3]=R.from_euler('z',pip if j==2 else pip*.62+dip,degrees=True).as_matrix()
   p[i]=p[parents[i]]@lr[i]@b
  return p
 def points_at(x):return (np.einsum('bij,bnj->ni',pose(x)[active],pre)@Gi.T)[:,:3]
 def residual(x):
  p=points_at(x);sd=sdf(p);out=[np.minimum(sd-.0007,0)*4500]
  # All three finger segments contribute, preventing fingertip-only pinching.
  for digit in digits:
   for j,ids in enumerate(segids[digit]):
    closest=np.sort(sd[ids])[:5].mean();weight=750 if variant=='vertical' else (750 if digit in ['index','middle'] else 40)
    out.append(np.array([(closest-.001)*weight]))
  for ids in [palmids,segids['thumb'][2]]:out.append(np.array([(np.sort(sd[ids])[:5].mean()-.001)*400]))
  # Neighbouring digits form a compact column with a small visible seam.
  for a,b in zip(digits,digits[1:]):
   aa=p[digitids[a]];bb=p[digitids[b]];gap=aa[:,2].min()-bb[:,2].max();out.append(np.array([(gap-.0007)*1800,min(gap-.0003,0)*5000]))
   # Finger centers retain vertical ordering.
   out.append(np.array([min(0,aa[:,2].mean()-bb[:,2].mean()-.013)*2500]))
  # Keep the original plane; allow only MCP flexion, coupled PIP/DIP, and a small palm fan.
  out.append((x[3::4]-np.array([4,1,-2,-4]))*.06)
  out.append((x[5::4]-65)*.012);out.append(x[6::4]*.025);out.append(x[:3]*.02)
  return np.concatenate(out)
 x0=np.array([0,0,0]+[0,10,65,0]*4,float);lo=np.array([-12,-18,-10]+[-10,-25,40,-8]*4,float);hi=np.array([12,18,10]+[10,45,85,12]*4,float)
 best=None
 for attempt in range(2):
  if best is not None:x0=best.x.copy();x0[4::4]+=3;x0=np.clip(x0,lo+.001,hi-.001)
  result=least_squares(residual,x0,bounds=(lo,hi),max_nfev=160,diff_step=.003,ftol=2e-5,xtol=2e-5,gtol=2e-5)
  if best is None or np.linalg.norm(result.fun)<np.linalg.norm(best.fun):best=result
  print(variant,attempt,np.linalg.norm(result.fun),result.x.tolist(),flush=True)
  p=pose(best.x);(d/'contact_solution.json').write_text(json.dumps({'parameters':best.x.tolist(),'residual':float(np.linalg.norm(best.fun)),'pose':{n:p[i].tolist() for i,n in enumerate(names)},'constraints':'MCP planar flexion, PIP 40..85, DIP coupled to PIP, metacarpal fan +-10 degrees; no local translations'},indent=2))
