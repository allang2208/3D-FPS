"""Small arm-only relaxation of the accepted left spellbook carry pose."""
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ThirdPersonBookCarryRelax20261010'
BASE = ROOT / 'SourceAssets/ThirdPersonStaffCarryClearance20261010/authored.json'
data = json.loads(BASE.read_text(encoding='utf-8'))
rig = json.loads((ROOT / 'SourceAssets/ThirdPersonStaffCast20261009/donors.json').read_text())
names, parents = data['names'], rig['parents']
upper, elbow, hand = [names.index(n) for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]


def world(local):
    result = local.copy()
    for i, p in enumerate(parents):
        if p >= 0:
            parent = R.from_quat(result[p, 3:7])
            result[i, :3] = result[p, :3] + parent.apply(local[i, :3] * result[p, 7:])
            result[i, 3:7] = (parent * R.from_quat(local[i, 3:7])).as_quat()
            result[i, 7:] = result[p, 7:] * local[i, 7:]
    return result


frames = []
for raw in data['clips']['Staff.BookCarry']['frames']:
    local = np.asarray(raw).copy()
    pose = world(local)
    # Jason faces +Y. A small backward shoulder swing lowers the whole support
    # chain, preserving its roll, wrist and hand-to-book relation.
    shoulder_swing = R.from_euler('x', -4.0, degrees=True)
    local[upper, 3:7] = (R.from_quat(pose[parents[upper], 3:7]).inv()
                         * shoulder_swing * R.from_quat(pose[upper, 3:7])).as_quat()
    pose = world(local)
    # Open the existing elbow bend slightly in its own plane. Descendant helper
    # bones follow the same segment; there is no separate wrist twist.
    hinge = np.cross(pose[elbow, :3] - pose[upper, :3], pose[hand, :3] - pose[elbow, :3])
    hinge /= np.linalg.norm(hinge)
    elbow_release = R.from_rotvec(hinge * np.deg2rad(-6.0))
    local[elbow, 3:7] = (R.from_quat(pose[parents[elbow], 3:7]).inv()
                         * elbow_release * R.from_quat(pose[elbow, 3:7])).as_quat()
    frames.append(local.tolist())

clip = dict(data['clips']['Staff.BookCarry'])
clip.update(frames=frames, source='Accepted Jason book support, shoulder -4 deg and elbow release 6 deg')
result = dict(mesh=data['mesh'], names=names, clips={'Staff.BookCarry': clip},
              source_parent=str(BASE.relative_to(ROOT)), book_mount=data['book_mount'],
              parameters={'shoulder_back_degrees': 4.0, 'elbow_release_degrees': 6.0},
              scope='Left arm rotations only; preserve local wrist, fingers, helper tracks and prop mount.',
              runtime_tested=False)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'authored.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
print('BOOK_CARRY_RELAX_AUTHORED', len(frames), 'frames')
