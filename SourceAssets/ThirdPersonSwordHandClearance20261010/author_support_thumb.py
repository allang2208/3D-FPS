"""Fit the support thumb to its own grip; preserve every accepted arm/wrist key.

Uses the already captured native equipment finger pose and Jason source skin.
The skin envelope is a modelling constraint, not an engine/runtime test.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = ROOT / 'SourceAssets/ThirdPersonDashArm20261010'
helper = ROOT / 'SourceAssets/ThirdPersonSwordGrip20261007/refine_kwang_grip.py'
ns = {'__file__': str(helper)}
exec(compile(helper.read_text().split('clips={}')[0], str(helper), 'exec'), ns)
names, parents, ref = ns['names'], ns['parents'], ns['ref']
ix = {name: i for i, name in enumerate(names)}
mul, inv, rot, between = (ns[key] for key in ('mul', 'inv', 'rot', 'between'))
source = json.loads((BASE / 'candidate-actions.json').read_text())
capture = json.loads((BASE / 'graph-after.json').read_text())['dash_samples'][0]
native = np.array([capture['actual_local'][name] for name in names])
geometry = json.loads((ROOT / 'SourceAssets/JasonPlayer20261003/Jason.json').read_text())


def fk(frame):
    world = frame.copy()
    for i, parent in enumerate(parents):
        if parent >= 0:
            world[i, :3] = world[parent, :3] + rot(world[parent, 3:7], frame[i, :3] * world[parent, 7:])
            world[i, 3:7] = mul(world[parent, 3:7], frame[i, 3:7])
            world[i, 7:] = world[parent, 7:] * frame[i, 7:]
    return world


def matrices(frame):
    world = fk(frame)
    result = np.zeros((len(names), 4, 4))
    result[:, 3, 3] = 1.
    result[:, :3, :3] = R.from_quat(world[:, 3:7]).as_matrix() * world[:, None, 7:]
    result[:, :3, 3] = world[:, :3]
    return result


world = fk(native)
weapon = ns['compose'](ns['compose'](world[ix['hand_r'], :7], ns['hand_to_weapon']),
    np.r_[0., 0., 0., ns['axis']([0, 0, 1], -math.radians(capture['grip_roll']))])
shaft = rot(weapon[3:7], np.array([0., 0., 1.]))
inverse_bind = np.linalg.inv(matrices(ref))
points = np.array(geometry['positions'])
hand_ids = {}
for side in ('r', 'l'):
    bones = {ix['hand_' + side]}
    for i, parent in enumerate(parents):
        if parent in bones:
            bones.add(i)
    hand_ids[side] = np.array([i for i, weights in enumerate(geometry['weights'])
        if sum(weight for bone, weight in weights if bone in bones) > .95])
weights_by_bone = {}
for i in np.concatenate(list(hand_ids.values())):
    for bone, weight in geometry['weights'][i]:
        weights_by_bone.setdefault(bone, []).append((i, weight))
weights_by_bone = {b: (np.array(rows)[:, 0].astype(int), np.array(rows)[:, 1, None])
                   for b, rows in weights_by_bone.items()}


def envelope(frame):
    transforms = matrices(frame) @ inverse_bind
    result = np.zeros_like(points)
    for bone, (ids, weights) in weights_by_bone.items():
        result[ids] += (points[ids] @ transforms[bone, :3, :3].T + transforms[bone, :3, 3]) * weights
    z = (result - weapon[:3]) @ shaft
    return float(z[hand_ids['r']].min() - z[hand_ids['l']].max())


thumb = [ix['thumb_%02d_l' % j] for j in (1, 2, 3)]
thumb_bones = [i for i, name in enumerate(names) if name.startswith('thumb_') and name.endswith('_l')]


def fit_thumb(drop):
    frame = native.copy()
    a, b, c = thumb
    start = world[a, :3]
    end = world[c, :3] - shaft * drop
    pole = world[b, :3] - shaft * drop * .5
    l1, l2 = np.linalg.norm(world[b, :3] - start), np.linalg.norm(world[c, :3] - world[b, :3])
    direction = ns['unit'](end - start)
    distance = np.linalg.norm(end - start)
    if not abs(l1 - l2) < distance < l1 + l2:
        raise RuntimeError('Support thumb target is outside its native bone reach.')
    bend = ns['unit'](pole - start - direction * np.dot(pole - start, direction))
    along = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
    joint = start + direction * along + bend * math.sqrt(max(0., l1 * l1 - along * along))
    desired = [mul(between(world[b, :3] - start, joint - start), world[a, 3:7]),
               mul(between(world[c, :3] - world[b, :3], end - joint), world[b, 3:7]),
               world[c, 3:7]]
    for bone, rotation in zip(thumb, desired):
        current = fk(frame)
        frame[bone, 3:7] = mul(inv(current[parents[bone], 3:7]), rotation)
    # The skin's half-joint helpers must follow the corrected finger rotation.
    for bone in thumb_bones:
        parent = parents[bone]
        if '_half_' in names[bone] and parent in thumb:
            delta = mul(inv(ref[parent, 3:7]), frame[parent, 3:7])
            half = R.from_rotvec(R.from_quat(inv(delta)).as_rotvec() * .5).as_quat()
            frame[bone, 3:7] = mul(half, ref[bone, 3:7])
    return frame


# Lower the extended thumb onto its own index-finger area, without translating
# wrists, palms or finger bones. Leave at least 6.5 mm to the upper-hand envelope.
required_gap = .65
selected = None
for drop in np.arange(.1, 2.61, .1):
    candidate = fit_thumb(float(drop))
    gap = envelope(candidate)
    if gap >= required_gap:
        selected = candidate
        break
if selected is None:
    raise RuntimeError('The bounded thumb fit cannot provide the requested hand separation.')

for clip in source['clips'].values():
    for frame in clip['frames']:
        for bone in thumb_bones:
            # Retain original translations/scales and every non-thumb key.
            frame[bone][3:7] = selected[bone, 3:7].tolist()
    clip['curves']['SwordSupportThumb'] = [1.] * len(clip['frames'])
source['provenance'] += '; support thumb fitted below upper-hand pinky, accepted arms/wrists unchanged'
source['accepted_arms_sha256'] = hashlib.sha256((BASE / 'candidate-actions.json').read_bytes()).hexdigest()
report = {
    'authoring_only': True, 'gameplay_test': False,
    'scope': list(source['clips']),
    'thumb_distal_target_drop_cm': float(drop),
    'source_skin_axial_clearance_cm': gap,
    'previous_source_skin_axial_clearance_cm': envelope(native),
    'changed_rotation_tracks': [names[i] for i in thumb_bones],
    'preserved': 'all arm and wrist tracks; all translations and scales; right hand; body, timing and grip-roll curves',
    'rotation_adjustments_degrees': {names[i]: float(np.degrees(R.from_quat(mul(inv(native[i, 3:7]), selected[i, 3:7])).magnitude())) for i in thumb},
    'accepted_arms_sha256': source['accepted_arms_sha256'],
    'native_grip_capture': str(BASE / 'graph-after.json')
}
(OUT / 'candidate-actions.json').write_text(json.dumps(source, separators=(',', ':')))
(OUT / 'hand-fit.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))
