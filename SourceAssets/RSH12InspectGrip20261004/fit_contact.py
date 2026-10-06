"""Bounded rigid hand placement and local finger rotations; no skin/bone scaling."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import least_squares
O=Path(__file__).parent
family,side,kind=sys.argv[1:4]
data=np.load(O/(f'input_{family}_{side}_{kind}.npz'))
names=list(data['names']);parents=data['parents'];base=data['world'].astype(np.float64);local=data['local'].astype(np.float64);used=data['used'];labels=data['labels']
weights=data['weights'];bound=data['bound'];hand=names.index('hand_'+side)
chain=[i for i,n in enumerate(names) if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))]
sdf=np.load(O/'grip_sdf.npz');axes=[sdf[a] for a in ('x','y','z')];lower=np.array([a[0] for a in axes]);upper=np.array([a[-1] for a in axes])
field=RegularGridInterpolator(axes,sdf['field'],bounds_error=False,fill_value=None)
def distance(points):
    q=np.clip(points,lower,upper)
    return (field(q)+np.linalg.norm(points-q,axis=1))*1000.
params=[('move',a) for a in range(3)]+[('wrist',a) for a in range(3)]+[(names[i],a) for i in chain for a in (0,2)]
limits=np.array([10.]*3+[12.]*3+[12. if 'metacarpal' in n else 35. if n.startswith(('index','thumb')) else 50. for n,a in params[6:]])
def pose(x):
    p=base.copy()
    # Placement is in grip space; wrist rotation is local, about the wrist.
    p[hand,:3,3]+=x[:3]*.001
    p[hand,:3,:3]=base[hand,:3,:3]@Rotation.from_rotvec(np.radians(x[3:6])).as_matrix()
    rr=np.zeros((len(chain),3));rr[:,(0,2)]=np.radians(x[6:].reshape(-1,2))
    rotations=Rotation.from_rotvec(rr).as_matrix()
    for k,i in enumerate(chain):
        li=local[i].copy();li[:3,:3]=li[:3,:3]@rotations[k]
        p[i]=p[parents[i]]@li
    return p
def points(x,indices):
    p=pose(x)
    return np.einsum('bij,bpj,pb->pi',p[used],bound[:,indices],weights[indices],optimize=True)[:,:3]
indices=np.arange(0,len(labels),3)
tip_groups=[np.flatnonzero(labels=='%s_03_%s'%(f,side)) for f in ('middle','ring','pinky')]
def residual(x):
    d=distance(points(x,indices))
    inside=np.minimum(d-.15,0.)
    # Every mixed-weight skin point contributes. The worst contacts cannot hide in an average.
    r=[inside*.5,np.sort(inside)[:80]*1.8,x[:3]*.11,x[3:6]*.045,x[6:]*.025]
    for g in tip_groups:
        if len(g):r.append(np.array([max(0.,distance(points(x,g)).min()-.8)*1.6]))
    return np.concatenate(r)
x=np.zeros(len(params));initial=residual(x)
out=O/(f'fit_{family}_{side}_{kind}.json')
if out.exists():x=np.array(json.loads(out.read_text())['parameters'])
for stage in range(2):
    if stage:indices=np.arange(len(labels))
    result=least_squares(residual,x,bounds=(-limits,limits),diff_step=.001,max_nfev=100,ftol=2e-5,xtol=2e-5,gtol=1e-4)
    x=result.x
    d=distance(points(x,np.arange(len(labels))))
    print('FIT',family,side,kind,'stage',stage,'cost',round(result.cost,3),'inside',int((d<-.5).sum()),'depth',round(max(0,-d.min()),3),'handmm',x[:3].round(3).tolist(),flush=True)
p=pose(x);rots={}
for i in chain:
    lp=np.linalg.inv(p[parents[i]])@p[i]
    delta=lp[:3,:3]@np.linalg.inv(local[i,:3,:3])
    rots[names[i]]=Rotation.from_matrix(delta).as_quat().tolist()
obj=dict(family=family,side=side,kind=kind,parameters=x.tolist(),parameter_names=params,offset_grip_m=(x[:3]*.001).tolist(),wrist_local_quat=Rotation.from_rotvec(np.radians(x[3:6])).as_quat().tolist(),finger_local_delta=rots,sdf_penetration_max_mm=float(max(0,-d.min())),sdf_inside_half_mm=int((d<-.5).sum()),cost=float(result.cost),source='RSH12Speedloader20261003 mesh and profiles')
out.write_text(json.dumps(obj,indent=2))
