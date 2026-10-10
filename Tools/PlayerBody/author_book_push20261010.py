"""Native left-arm book shove, starting from the current relaxed book carry."""
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicHermiteSpline, PchipInterpolator
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ThirdPersonBookPush20261010'
SOURCE = ROOT / 'SourceAssets/ThirdPersonBookCarryRelax20261010/authored.json'
data = json.loads(SOURCE.read_text())
rig = json.loads((ROOT / 'SourceAssets/ThirdPersonStaffCast20261009/donors.json').read_text())
names, parents = data['names'], rig['parents']
upper, elbow, hand = [names.index(n) for n in ('upperarm_l','lowerarm_l','hand_l')]
carry = np.asarray(data['clips']['Staff.BookCarry']['frames'][0])

def world(local):
    result = local.copy()
    for i, p in enumerate(parents):
        if p >= 0:
            parent = R.from_quat(result[p,3:7])
            result[i,:3] = result[p,:3] + parent.apply(local[i,:3] * result[p,7:])
            result[i,3:7] = (parent * R.from_quat(local[i,3:7])).as_quat()
            result[i,7:] = result[p,7:] * local[i,7:]
    return result

base = world(carry)
hinge = np.cross(base[elbow,:3]-base[upper,:3],base[hand,:3]-base[elbow,:3])
hinge /= np.linalg.norm(hinge)
local_hinge = R.from_quat(base[upper,3:7]).inv().apply(hinge)
times = [0.,.025,.055,.14,.185,.24,.43]
pitch = [0.,-2.,12.,55.,58.,35.,0.]
# A small cock keeps the elbow on the support plane; a deep early fold
# concentrates the lift into the first 50 ms despite a smooth shoulder curve.
flex = [0.,3.,5.,-5.,-7.,3.,0.]
yaw = [0.,0.,0.,4.,4.,2.,0.]
def curve(values):
    slopes = PchipInterpolator(times,values).derivative()(times)
    slopes[0] = slopes[-1] = 0.
    return CubicHermiteSpline(times,values,slopes)
pitch_curve, flex_curve, yaw_curve = map(curve,(pitch,flex,yaw))
frames = []
for t in np.linspace(0.,.43,130):
    local = carry.copy()
    group = R.from_euler('z',float(yaw_curve(t)),degrees=True) * R.from_euler('x',float(pitch_curve(t)),degrees=True)
    local[upper,3:7] = (R.from_quat(base[parents[upper],3:7]).inv()*group*R.from_quat(base[upper,3:7])).as_quat()
    local[elbow,3:7] = (R.from_rotvec(local_hinge*np.deg2rad(float(flex_curve(t))))*R.from_quat(carry[elbow,3:7])).as_quat()
    frames.append(local)
frames[0]=carry.copy();frames[-1]=carry.copy()
for i in range(1,len(frames)):
    flip=np.sum(frames[i-1][:,3:7]*frames[i][:,3:7],axis=1)<0.
    frames[i][flip,3:7]*=-1.
result=dict(mesh=data['mesh'],names=names,source_parent=str(SOURCE.relative_to(ROOT)),book_mount=data['book_mount'],
    parameters=dict(times=times,pitch_degrees=pitch,elbow_flex_degrees=flex,yaw_degrees=yaw),
    clips={'Staff.BookPush':dict(rate=300,contact=.14/.43,release=.185/.43,
        frames=[f.tolist() for f in frames],source='Current native Jason left book carry; shoulder-led forward shove')},
    scope='Native left arm only; fixed local wrist, original fingers, bone lengths, helpers and book mount.',runtime_tested=False)
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('BOOK_PUSH_AUTHORED',len(frames),'frames, 0.43 seconds')
