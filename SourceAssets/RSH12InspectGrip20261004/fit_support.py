"""Move the support hand as a whole; retain its original finger shape and reload action."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np,json,sys
from pathlib import Path
from scipy.interpolate import RegularGridInterpolator
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
O=Path(__file__).parent;kind=sys.argv[1]
d=np.load(O/f'input_single_l_{kind}.npz');p=np.einsum('bij,bpj,pb->pi',d['world'][d['used']],d['bound'],d['weights'],optimize=True)[:,:3]
field=np.load(O/'full_sdf.npz');axes=[field[k] for k in ('x','y','z')];lo=np.array([a[0] for a in axes]);hi=np.array([a[-1] for a in axes]);sdf=RegularGridInterpolator(axes,field['field'],bounds_error=False,fill_value=None)
h=d['world'][list(d['names']).index('hand_l')].astype(float)
def distance(x):
    r=h[:3,:3]@Rotation.from_rotvec(np.radians(x[3:])).as_matrix()@np.linalg.inv(h[:3,:3]);pp=(p-h[:3,3])@r.T+h[:3,3]+x[:3]*.001;q=np.clip(pp,lo,hi)
    return (sdf(q)+np.linalg.norm(pp-q,axis=1))*1000
def residual(x):
    inside=np.minimum(distance(x)-1.,0.);return np.r_[inside*3.,np.sort(inside)[:60]*8.,x[:3]*.1,x[3:]*.3]
r=least_squares(residual,np.array((15.,0,0,0,0,0)),bounds=([0,-10,-10,-6,-6,-6],[30,10,10,6,6,6]),max_nfev=150,diff_step=.001)
x=r.x;ds=distance(x);print('SUPPORT_FIT',kind,x.round(2).tolist(),'depth',max(0,-ds.min()),flush=True)
(O/f'support_{kind}.json').write_text(json.dumps(dict(side='l',offset_grip_m=(x[:3]*.001).tolist(),wrist_local_quat=Rotation.from_rotvec(np.radians(x[3:])).as_quat().tolist(),finger_local_delta={}),indent=2))
