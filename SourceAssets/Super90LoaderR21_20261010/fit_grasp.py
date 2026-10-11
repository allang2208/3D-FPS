"""Make a cupped grasp at the real knob, using anatomical finger flexion."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
from scipy.optimize import least_squares
O=Path(__file__).parent
d=json.loads((O/'hand_inputs.json').read_text())
rest={n:np.array(m) for n,m in d['rest'].items()};pose={n:np.array(m) for n,m in d['pose'].items()}
opened={n:np.array(m) for n,m in d['open_pose'].items()};push={n:np.array(m) for n,m in d['push_pose'].items()}
parents=d['parents'];names=d['finger_names'];ri={n:np.linalg.inv(m) for n,m in rest.items()}
local={n:np.linalg.inv(opened[parents[n]])@opened[n] for n in names}
rest_local={n:np.linalg.inv(rest[parents[n]])@rest[n] for n in names}
v=np.array([s['position'] for s in d['skin']]);dom=[max(s['weights'],key=s['weights'].get) for s in d['skin']]
centers={n:v[np.array(dom)==n].mean(axis=0) for n in names if '_metacarpal_' not in n}
forward=rest['middle_01_l'][:3,3]-rest['hand_l'][:3,3];forward/=np.linalg.norm(forward)
width=rest['index_01_l'][:3,3]-rest['pinky_01_l'][:3,3];width/=np.linalg.norm(width)
palm=np.cross(forward,width);palm/=np.linalg.norm(palm)
u=rest['index_02_l'][:3,3]-rest['index_01_l'][:3,3];z=centers['index_03_l']-rest['index_03_l'][:3,3]
if np.dot(z/np.linalg.norm(z)-u/np.linalg.norm(u),palm)<0:palm=-palm
rot_names=[f'{digit}_{k:02}_l' for digit in ('index','middle','ring','pinky') for k in (1,2,3)]
axes={}
for n in rot_names:
    direction=centers[n]-rest[n][:3,3];direction/=np.linalg.norm(direction)
    axis=np.cross(direction,palm);axis/=np.linalg.norm(axis);axes[n]=rest[parents[n]][:3,:3].T@axis
seed=np.array([36,64,32, 42,68,35, 49,68,36, 54,64,33, 0,0,0,0,0,0],dtype=float)
def finger_locals(angles):
    out={n:m.copy() for n,m in local.items()}
    for n,a in zip(rot_names,angles):out[n][:3,:3]=R.from_rotvec(axes[n]*np.deg2rad(a)).as_matrix()@rest_local[n][:3,:3]
    # Use the native pusher grasp's thumb opposition, softened at the last two
    # joints. Thumb supports the side; it does not meet the index fingertip.
    for n in ('thumb_01_l','thumb_02_l','thumb_03_l'):
        p=np.linalg.inv(push[parents[n]])@push[n]
        t=.78 if n=='thumb_01_l' else .58
        out[n][:3,:3]=Slerp([0,1],R.from_matrix(np.stack((local[n][:3,:3],p[:3,:3]))))([t]).as_matrix()[0]
    return out
def build(a):
    loc=finger_locals(a[:12]);h=pose['hand_l'].copy()
    delta=np.eye(4);delta[:3,3]=a[12:15]*.001;delta[:3,:3]=R.from_rotvec(np.deg2rad(a[15:18])).as_matrix()
    h=h@delta;w={'hand_l':h}
    for n in names:w[n]=w[parents[n]]@loc[n]
    return w,loc,delta
bolt=pose['WPN_bolt']@ri['WPN_bolt'];knob=(bolt@np.r_[d['handle_rest_center'],1])[:3]
gd=pose['WPN_root']@ri['WPN_root'];muzzle=gd[:3,:3]@np.array([0,1,0]);muzzle/=np.linalg.norm(muzzle)
handle_axis=gd[:3,:3]@np.array([1,0,0]);handle_axis/=np.linalg.norm(handle_axis)
pads={n:(ri[n]@np.r_[centers[n]+palm*.0045,1])[:3] for n in ('index_02_l','middle_02_l')}
targets={'index_02_l':knob+muzzle*.006+handle_axis*.003,'middle_02_l':knob+muzzle*.005-handle_axis*.006}
def objective(a):
    w,_,_=build(a);contact=[]
    for n in pads:contact.extend(((w[n]@np.r_[pads[n],1])[:3]-targets[n])/(.005 if n.startswith('index') else .007))
    # A shaped, closed four-finger silhouette is a first-class objective; ring
    # and little fingers fold naturally without chasing the small knob.
    return np.r_[contact,(a[:12]-seed[:12])/np.array([14,15,10,12,14,10,8,10,8,8,10,8]),a[12:15]/5,a[15:18]/7]
low=[24,48,20, 30,50,22, 38,52,23, 40,48,22]+[-12]*3+[-12]*3
high=[60,82,46, 64,84,48, 66,82,48, 70,80,46]+[12]*3+[12]*3
fit=least_squares(objective,seed,bounds=(low,high),max_nfev=120)
w,loc,delta=build(fit.x)
out=dict(method='Cupped four-finger grasp; index/middle carry knob; thumb supports side',
    finger_local={n:m.tolist() for n,m in loc.items()},rotation_bones=names,
    wrist_local_delta=delta.tolist(),flexion_degrees=dict(zip(rot_names,fit.x[:12].tolist())),
    wrist_translation_mm=fit.x[12:15].tolist(),wrist_rotation_vector_degrees=fit.x[15:18].tolist(),
    anatomical_flexion_axes={n:a.tolist() for n,a in axes.items()},runtime_tested=False)
(O/'grasp_target.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('R21_GRASP_AUTHORED',json.dumps({k:out[k] for k in ('flexion_degrees','wrist_translation_mm','wrist_rotation_vector_degrees')}),flush=True)
