"""Fit anatomical flexion and retain the donor's index/thumb gesture."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np,json,sys
from pathlib import Path
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import least_squares
O=Path(__file__).parent
family,side,kind=sys.argv[1:4]
D=np.load(O/f'input_{family}_{side}_{kind}.npz');names=list(D['names']);parent=D['parents'];base=D['world'].astype(float);local=D['local'].astype(float)
used=D['used'];bound=D['bound'];weights=D['weights'];labels=D['labels'];hi=names.index('hand_'+side)
chain=[i for i,n in enumerate(names) if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))]
field=np.load(O/'grip_sdf_closed.npz');axes=[field[k] for k in ('x','y','z')];lo=np.array([a[0] for a in axes]);up=np.array([a[-1] for a in axes]);sdf=RegularGridInterpolator(axes,field['field'],bounds_error=False,fill_value=None)
def distances(points):
    q=np.clip(points,lo,up);return (sdf(q)+np.linalg.norm(points-q,axis=1))*1000
parameters=[];limits=[]
for i in chain:
    name=names[i];axis=np.cross(base[parent[i],:3,1],base[i,:3,1]);axis=base[i,:3,:3].T@axis
    if np.linalg.norm(axis)<.1:axis=np.array((0.,0.,1.))
    axis/=np.linalg.norm(axis)
    if 'metacarpal' in name:
        parameters.extend([(i,np.array((1.,0.,0.))),(i,np.array((0.,0.,1.)))]);limits.extend([5.,5.])
    else:
        parameters.append((i,axis));limits.append(15. if name.startswith(('thumb','index')) else 65.)
        if '_01_' in name:
            splay=np.cross(axis,np.array((0.,1.,0.)));splay/=np.linalg.norm(splay)
            parameters.append((i,splay));limits.append(12.)
limits=np.array([15.]*3+[8.]*3+limits)
def pose(x):
    p=base.copy();p[hi,:3,3]+=x[:3]*.001;p[hi,:3,:3]=base[hi,:3,:3]@R.from_rotvec(np.radians(x[3:6])).as_matrix()
    deltas={i:np.eye(3) for i in chain}
    for (i,axis),v in zip(parameters,x[6:]):deltas[i]=deltas[i]@R.from_rotvec(axis*np.radians(v)).as_matrix()
    for i in chain:
        li=local[i].copy();li[:3,:3]=li[:3,:3]@deltas[i];p[i]=p[parent[i]]@li
    return p
def pts(x,ids):return np.einsum('bij,bpj,pb->pi',pose(x)[used],bound[:,ids],weights[ids],optimize=True)[:,:3]
allids=np.arange(len(labels));x=np.zeros(len(limits));original=pts(x,allids)
tips={f:np.flatnonzero(labels==f+'_03_'+side) for f in ('thumb','index','middle','ring','pinky')}
means={f:original[g].mean(0) for f,g in tips.items()}
ids=allids[::3]
def residual(x):
    points=pts(x,allids);d=distances(points[ids]);inside=np.minimum(d-.3,0)
    r=[inside*.5,np.sort(inside)[:60]*1.8,x[:3]*.13,x[3:6]*.18,x[6:]*.12]
    for f in ('index','thumb'):
        # Keep the straight inspection finger / firing finger and thumb on the same gun feature.
        r.append((points[tips[f]].mean(0)-means[f])*1000*2.5)
    for f in ('middle','ring'):
        m=points[tips[f]].mean(0)
        target=means[f].copy();target[0]=.024 if side=='r' else -.024
        r.append((m-target)*1000*np.array((1.8,.7,.7)))
    for f in ('middle','ring','pinky'):
        r.append(np.array([max(0,distances(points[tips[f]]).min()-.8)*1.8]))
    return np.concatenate(r)
path=O/f'natural_{family}_{side}_{kind}.json'
if path.exists():x=np.array(json.loads(path.read_text())['parameters'])
for stage in range(2):
    if stage:ids=allids
    result=least_squares(residual,x,bounds=(-limits,limits),max_nfev=130,diff_step=.001,ftol=1e-5,xtol=1e-5)
    x=result.x;ds=distances(pts(x,allids));print('NATURAL_FIT',family,side,kind,stage,round(result.cost,2),round(max(0,-ds.min()),3),int((ds<-.5).sum()),x[:6].round(2).tolist(),flush=True)
p=pose(x);deltas={}
for i in chain:
    lp=np.linalg.inv(p[parent[i]])@p[i];deltas[names[i]]=R.from_matrix(lp[:3,:3]@np.linalg.inv(local[i,:3,:3])).as_quat().tolist()
path.write_text(json.dumps(dict(family=family,side=side,kind=kind,parameters=x.tolist(),offset_grip_m=(x[:3]*.001).tolist(),wrist_local_quat=R.from_rotvec(np.radians(x[3:6])).as_quat().tolist(),finger_local_delta=deltas,sdf_penetration_max_mm=float(max(0,-ds.min())),sdf_inside_half_mm=int((ds<-.5).sum()),cost=float(result.cost)),indent=2))
