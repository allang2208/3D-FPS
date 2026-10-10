"""Author a native staff strike from the accepted carry, preserving the grip."""
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicHermiteSpline, PchipInterpolator
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ThirdPersonStaffStrikeCarry20261010'
SOURCE = ROOT / 'SourceAssets/ThirdPersonStaffCarryClearance20261010/authored.json'
data = json.loads(SOURCE.read_text(encoding='utf-8'))
rig = json.loads((ROOT / 'SourceAssets/ThirdPersonStaffCast20261009/donors.json').read_text())
names, parents = data['names'], rig['parents']
upper, elbow, hand = [names.index(n) for n in ('upperarm_r', 'lowerarm_r', 'hand_r')]
carry = np.asarray(data['clips']['Staff.NativeArm.Carry']['frames'][0])


def world(local):
    result = local.copy()
    for i, p in enumerate(parents):
        if p >= 0:
            parent = R.from_quat(result[p, 3:7])
            result[i, :3] = result[p, :3] + parent.apply(local[i, :3] * result[p, 7:])
            result[i, 3:7] = (parent * R.from_quat(local[i, 3:7])).as_quat()
            result[i, 7:] = result[p, 7:] * local[i, 7:]
    return result


base = world(carry)
hinge = np.cross(base[elbow, :3] - base[upper, :3], base[hand, :3] - base[elbow, :3])
hinge /= np.linalg.norm(hinge)
local_hinge = R.from_quat(base[upper, 3:7]).inv().apply(hinge)
mount = R.from_quat(data['staff_mount'][3:7])
shaft = (R.from_quat(base[hand, 3:7]) * mount).apply([0., 0., 1.])

# Match StaffPrimaryAttackMotion's normalized windup/contact/follow-through
# contract. Shape-preserving curves carry velocity through contact, with a
# slower lift, fast downstroke, braking follow-through and eased recovery.
times = [0., .18, .40, .60, .70, .82, 1.]
pitch_degrees = [0., -18., -52., 52., 68., 36., 0.]
extension_degrees = [0., -3., -4., 32., 42., 24., 0.]
def motion_curve(values):
    slopes = PchipInterpolator(times, values).derivative()(times)
    slopes[0] = slopes[-1] = 0.
    return CubicHermiteSpline(times, values, slopes)


pitch = motion_curve(pitch_degrees)
extension = motion_curve(extension_degrees)
frames = []
for time in np.linspace(0., 1., 61):
    local = carry.copy()
    local[elbow, 3:7] = (R.from_rotvec(local_hinge * np.deg2rad(-float(extension(time))))
                         * R.from_quat(carry[elbow, 3:7])).as_quat()
    pose = world(local)
    current = (R.from_quat(pose[hand, 3:7]) * mount).apply([0., 0., 1.])
    desired = R.from_euler('x', -float(pitch(time)), degrees=True).apply(shaft)
    # Stage the entire arm, never the wrist. The carry's positive shaft X is
    # retained so the long lower end remains outside the right hip throughout.
    swing = R.align_vectors([desired], [current])[0]
    local[upper, 3:7] = (R.from_quat(base[parents[upper], 3:7]).inv()
                         * swing * R.from_quat(base[upper, 3:7])).as_quat()
    frames.append(local)
frames[0] = carry.copy()
frames[-1] = carry.copy()
for i in range(1, len(frames)):
    flip = np.sum(frames[i-1][:, 3:7] * frames[i][:, 3:7], axis=1) < 0.
    frames[i][flip, 3:7] *= -1.
result = dict(mesh=data['mesh'], names=names, source_parent=str(SOURCE.relative_to(ROOT)),
              source_url=data['source_url'], staff_mount=data['staff_mount'],
              parameters=dict(times=times, pitch_degrees=pitch_degrees, extension_degrees=extension_degrees),
              clips={'Staff.FullBody.Strike': dict(rate=60, contact=.60, release=.70,
                     frames=[f.tolist() for f in frames], source='Current native staff carry, whole-arm strike')},
              scope='Right native arm only; existing wrist, finger and equipment mount preserved.',
              runtime_tested=False)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'authored.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
print('STAFF_STRIKE_CARRY_AUTHORED', len(frames), 'frames')
