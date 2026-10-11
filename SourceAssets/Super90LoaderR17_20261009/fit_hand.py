"""Author a partial two-finger hook on the existing R16 wrist path.

Only anatomical finger flexion and a small palm swing are available to the fit.
No shoulder/elbow/wrist translation, bone stretch, or skin weight is a variable.
The visible reference is frames 293-308 of the user's Delta Force capture.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
O=Path(__file__).parent
d=json.loads((O/'hand_inputs.json').read_text())
rest={n:np.array(m) for n,m in d['rest'].items()}
pose={n:np.array(m) for n,m in d['pose'].items()}
opened={n:np.array(m) for n,m in d['open_pose'].items()}
parents=d['parents'];names=d['finger_names']
local={n:np.linalg.inv(opened[parents[n]])@opened[n] for n in names}
rest_local={n:np.linalg.inv(rest[parents[n]])@rest[n] for n in names}
ri={n:np.linalg.inv(m) for n,m in rest.items()}
skin=d['skin'];v=np.array([s['position'] for s in skin]);dominant=[max(s['weights'],key=s['weights'].get) for s in skin]
centers={n:v[np.array(dominant)==n].mean(axis=0) for n in names if '_metacarpal_' not in n}
forward=rest['middle_01_l'][:3,3]-rest['hand_l'][:3,3];forward/=np.linalg.norm(forward)
width=rest['index_01_l'][:3,3]-rest['pinky_01_l'][:3,3];width/=np.linalg.norm(width)
palm=np.cross(forward,width);palm/=np.linalg.norm(palm)
# Choose flexion toward the existing anatomical rest curvature, not bone +Y.
u=rest['index_02_l'][:3,3]-rest['index_01_l'][:3,3]
z=centers['index_03_l']-rest['index_03_l'][:3,3]
if np.dot(z/np.linalg.norm(z)-u/np.linalg.norm(u),palm)<0:palm=-palm
axes={}
for n in names:
    if '_metacarpal_' in n or n.startswith('thumb'):continue
    direction=centers[n]-rest[n][:3,3];direction/=np.linalg.norm(direction)
    axis=np.cross(direction,palm);axis/=np.linalg.norm(axis)
    axes[n]=rest[parents[n]][:3,:3].T@axis
def qmat(axis,angle):return R.from_rotvec(axis*np.deg2rad(angle)).as_matrix()
seed=np.array([5,45,22, 8,42,24, 7,22,12, 5,18,10],dtype=float)
rot_names=[f'{digit}_{k:02}_l' for digit in ('index','middle','ring','pinky') for k in (1,2,3)]
def finger_locals(angles):
    out={n:m.copy() for n,m in local.items()}
    for n,a in zip(rot_names,angles):out[n][:3,:3]=qmat(axes[n],a)@rest_local[n][:3,:3]
    # The reference thumb stays out of the grasp; keep its base roll and spread,
    # then release the distal joints toward their anatomical open shape.
    for n in ('thumb_02_l','thumb_03_l'):out[n][:3,:3]=rest_local[n][:3,:3]
    return out
def build(angles):
    loc=finger_locals(angles);w={'hand_l':pose['hand_l']}
    for n in names:w[n]=w[parents[n]]@loc[n]
    return w,loc
bolt=pose['WPN_bolt']@ri['WPN_bolt']
knob=(bolt@np.r_[d['handle_rest_center'],1])[:3]
# Pulling pad meets the muzzle-facing side of the knob; the middle finger
# follows as a relaxed secondary hook, rather than forcing two fingertips
# onto the same small Super90 knob.
gun_deform=pose['WPN_root']@ri['WPN_root']
muzzle=gun_deform[:3,:3]@np.array([0,1,0]);muzzle/=np.linalg.norm(muzzle)
pad_rest=centers['index_02_l']+palm*.005
pad_local=(ri['index_02_l']@np.r_[pad_rest,1])[:3]
target=knob+muzzle*.006
def objective(a):
    w,_=build(a)
    pad=(w['index_02_l']@np.r_[pad_local,1])[:3]
    # Bias strongly to the reference silhouette; contact only fits the hook's
    # first two flexion angles. Ring/pinky remain independently relaxed.
    return np.r_[(pad-target)/.005,(a-seed)/np.array([28,35,22,12,15,12,8,10,8,8,10,8])]
fit=least_squares(objective,seed,bounds=([-12,22,8, -3,25,10, 0,10,3, 0,8,3],
                                      [35,82,42, 25,65,40, 20,38,27, 18,32,25]),max_nfev=100)
w,loc=build(fit.x)
out={'method':'Reference partial hook; anatomical flexion; accepted wrist rotation and all arm motion fixed',
     'reference_frames':[293,298,302,308], 'hand_rotation_changed':False,
     'rotation_bones':names,'finger_local':{n:m.tolist() for n,m in loc.items()},
     'open_local':{n:m.tolist() for n,m in local.items()},
     'flexion_degrees':dict(zip(rot_names,fit.x.tolist())),
     'authoring_pad_offset_mm':float(np.linalg.norm((w['index_02_l']@np.r_[pad_local,1])[:3]-target)*1000),
     'runtime_tested':False}
(O/'hand_target.json').write_text(json.dumps(out,indent=2))
print('HAND_TARGET_SAVED',out['flexion_degrees'],'pad offset mm',out['authoring_pad_offset_mm'])
