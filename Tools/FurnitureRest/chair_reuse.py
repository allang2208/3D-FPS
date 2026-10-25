"""Fit the V5/V6/V7 seating family to the six existing chair/bench types."""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/FurnitureRest20261022/ChairReuse20261024'
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
ns = {'__file__': str(ROOT / 'Tools/FurnitureRest/refine.py')}
exec((ROOT / 'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0], ns)
fk, rot, ik, handrot, ix, ref, bind = [ns[k] for k in ('fk', 'rot', 'ik', 'handrot', 'ix', 'ref', 'bind')]

def blendrot(a, b, t):
    return Slerp([0, 1], R.from_matrix(np.array([a, b])))(float(np.clip(t, 0, 1))).as_matrix()


# Reuse V6's hanging-arm definition without running its asset authoring loop.
tree = ast.parse((ROOT / 'Tools/FurnitureRest/hanging_entry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                            and n.name in ('smooth', 'hanging')], type_ignores=[]),
             'hanging_entry.py', 'exec'))
donor_path = ROOT / 'SourceAssets/FurnitureRest20261022/HangingEntryV6/authored.json'
baseline_path = ROOT / 'SourceAssets/FurnitureRest20261022/RefineV2/authored.json'
donor = read(donor_path)
baseline = read(baseline_path)
config = read(ROOT / 'Content/ColdSteelData/furniture_rest.json')
body = read(ROOT / 'Content/ColdSteelData/player_body.json')
specs = {
    'Chair': {'depth': 8., 'hands': 'lap'},
    'Chair50': {'depth': 8., 'hands': 'armrests', 'wrist': [29., -15., 70.9]},
    'Chair52': {'depth': 14., 'hands': 'armrests', 'wrist': [32., -19., 76.5]},
    'Chair53': {'depth': 10., 'hands': 'lap'},
    'Chair55': {'depth': 14., 'hands': 'lap'},
    'Bench': {'depth': 8., 'hands': 'lap'},
}
result = {k: donor[k] for k in ('mesh', 'skeleton', 'names', 'parents', 'reference')}
result['clips'] = {}
metadata = {}

def sample(take, seconds):
    frames = take['frames']
    x = float(np.clip(seconds * take['rate'], 0, len(frames) - 1))
    i = min(int(x), len(frames) - 2)
    a, b = np.array(frames[i]), np.array(frames[i + 1])
    t = x - i
    f = a * (1 - t) + b * t
    q = b[:, 3:7].copy()
    q[(a[:, 3:7] * q).sum(axis=1) < 0] *= -1
    f[:, 3:7] = a[:, 3:7] * (1 - t) + q * t
    f[:, 3:7] /= np.linalg.norm(f[:, 3:7], axis=1)[:, None]
    return f


def unit(v):
    return v / max(np.linalg.norm(v), 1e-9)


def basis(direction, normal):
    y = unit(direction)
    z = unit(normal - y * (normal @ y))
    return np.column_stack((np.cross(y, z), y, z))


relaxed_world = fk(sample(donor['clips']['Rest.Sofa.Idle'], 0.))
relaxed_pelvis = relaxed_world[ix['pelvis'], :3, 3]


# Use the seated donor's anatomical knee plane, as in the bed hinge repair.
leg_pose = fk(sample(donor['clips']['Rest.Sofa.Enter'], 1.15))
leg_reference = {}
for side in ('l', 'r'):
    a, b, c = [ix[n + '_' + side] for n in ('thigh', 'calf', 'foot')]
    h, k, e = leg_pose[[a, b, c], :3, 3]
    normal = unit(np.cross(k - h, e - k))
    leg_reference[side] = (np.linalg.norm(k - h), np.linalg.norm(e - k),
                           basis(k - h, normal), basis(e - k, normal))


def leg(f, side, target, foot_rotation):
    a, b, c = [ix[n + '_' + side] for n in ('thigh', 'calf', 'foot')]
    h = fk(f)[a, :3, 3]
    l1, l2, b1, b2 = leg_reference[side]
    v = target - h
    distance = np.clip(np.linalg.norm(v), abs(l1 - l2) + .05, l1 + l2 - .35)
    direction = unit(v)
    pole = np.array([20. if side == 'l' else -20., 100., 20.])
    bend = unit(pole - direction * (pole @ direction))
    along = (l1*l1 + distance*distance - l2*l2) / (2*distance)
    knee = h + direction*along + bend*math.sqrt(max(0., l1*l1 - along*along))
    end = h + direction*distance
    normal = unit(np.cross(knee - h, end - knee))
    rot(f, a, basis(knee - h, normal) @ b1.T @ leg_pose[a, :3, :3])
    rot(f, b, basis(end - knee, normal) @ b2.T @ leg_pose[b, :3, :3])
    rot(f, c, foot_rotation)


def fit(kind, phase, t):
    spec = specs[kind]
    f = sample(donor['clips']['Rest.Sofa.' + phase], t)
    # Keep the established per-chair seat/floor heights. The sofa supplies
    # the pacing and upper body; its 65 cm cushion is not copied onto chairs.
    old_t = float(np.interp(t, [0., .5, 1.15, 2.05, 2.8], [0., .45, 1.25, 1.7, 1.85])) if phase == 'Enter' else t
    old = sample(baseline['clips'][f'Rest.{kind}.{phase}'], old_t)
    original_world = fk(old)
    settle = smooth((t - 1.15) / .9) if phase == 'Enter' else 1.
    f[ix['pelvis'], :3] = old[ix['pelvis'], :3]
    f[ix['pelvis'], 1] -= spec['depth'] * settle
    for side in ('l', 'r'):
        foot = ix['foot_' + side]
        # Deep seating uses the donor's hanging calves. Forcing its ankles
        # onto a lower floor overextends the legs and sinks the thighs.
        relaxed_foot = f[ix['pelvis'], :3] + relaxed_world[foot, :3, 3] - relaxed_pelvis
        foot_target = original_world[foot, :3, 3]*(1-settle) + relaxed_foot*settle
        foot_rotation = blendrot(original_world[foot, :3, :3], relaxed_world[foot, :3, :3], settle)
        leg(f, side, foot_target, foot_rotation)

    for side, sign in (('l', 1), ('r', -1)):
        supported = spec['hands'] == 'armrests'
        start = (.55 if side == 'l' else .68) if supported else (.68 if side == 'l' else .8)
        finish = (2.18 if side == 'l' else 2.32) if supported else (2.36 if side == 'l' else 2.5)
        reach = smooth((t - start) / (finish - start)) if phase == 'Enter' else 1.
        h = hanging(f, side, sign, t, phase)
        hw = fk(h)
        w = fk(f)
        if supported:
            target = np.array(spec['wrist']) * [sign, 1, 1]
            forward, normal = np.array([sign*.025, 1., -.06]), np.array([0., -.06, -1.])
            donor_kind = 'SofaRight' if side == 'l' else 'SofaLeft'
        else:
            target = f[ix['pelvis'], :3] + relaxed_world[ix['hand_' + side], :3, 3] - relaxed_pelvis
            # Open the donor's resting fingers before seating the palm on the
            # thigh. Its inward-curled thumb otherwise enters the leg surface.
            target += [sign*1.5, 0., 2.5]
            forward, normal = np.array([-sign*.16, 1., -.13]), np.array([sign*.08, -.13, -1.])
            donor_kind = 'SofaRight' if side == 'l' else 'SofaLeft'
        rest = sample(donor['clips'][f'Rest.{donor_kind}.Idle'], t if phase == 'Idle' else 0.)
        desired = f.copy()
        handrot(desired, side, forward, normal)
        desired_rotation = fk(desired)[ix['hand_' + side], :3, :3]
        cl = ix['clavicle_' + side]
        f[cl, 3:7] = h[cl, 3:7]
        hand = hw[ix['hand_' + side], :3, 3]*(1-reach) + target*reach
        hand += np.array([sign*4., 1., 24. if supported else 4.])*math.sin(math.pi*reach)
        if phase == 'Enter' and not supported:
            # On the lower seats, let the hanging thumb pass outside the
            # thigh before the hand turns inward toward its resting place.
            hand[0] += sign*2.*smooth(t/.35)*(1-smooth((t-1.15)/.55))
        shoulder = fk(f)[ix['upperarm_' + side], :3, 3]
        end_pole = shoulder + np.array([sign*20., -15. if supported else 8., -30.])
        pole = hw[ix['lowerarm_' + side], :3, 3]*(1-reach) + end_pole*reach
        ik(f, side, ('upperarm', 'lowerarm', 'hand'), hand, pole)
        rot(f, ix['hand_' + side], blendrot(hw[ix['hand_' + side], :3, :3], desired_rotation, smooth(reach)))
        for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            for joint in (1, 2, 3):
                i = ix[f'{digit}_{joint:02d}_{side}']
                f[i, 3:7] = R.from_matrix(blendrot(R.from_quat(h[i, 3:7]).as_matrix(),
                                                  R.from_quat(rest[i, 3:7]).as_matrix(),
                                                  smooth((reach-.05)/.95))).as_quat()
    return f


for kind in specs:
    enter = [fit(kind, 'Enter', t).tolist() for t in np.linspace(0., 2.8, 85)]
    idle = [fit(kind, 'Idle', t).tolist() for t in np.linspace(0., 4., 121)]
    # Idle starts at the exact settled entry pose; breathe with the V5 spine.
    idle[0] = copy.deepcopy(enter[-1])
    idle[-1] = copy.deepcopy(enter[-1])
    leave = copy.deepcopy(enter[::-1])
    leave.extend(copy.deepcopy(enter[0]) for _ in range(9))
    for phase, frames in (('Enter', enter), ('Idle', idle), ('Exit', leave)):
        role = f'Rest.{kind}.{phase}'
        duration = (len(frames)-1)/30
        result['clips'][role] = {'rate': 30, 'duration': duration, 'frames': frames}
        camera = []
        for frame in frames:
            head = fk(np.array(frame))[ix['head']]
            eye = head[:3, 3] + head[:3, :3] @ bind[ix['head'], :3, :3].T @ np.array([0., 7., 6.])
            camera.append([*eye.tolist(), 0., 0.])
        metadata[role] = {'duration': duration, 'camera': camera}
    print('CHAIR_REUSE_AUTHORED', kind, flush=True)

roles = list(result['clips'])
inventory = [p for p in config['furniture'] if any(s['kind'] in specs for s in p['slots'])]
baseline_routes = {'default': {r: body['clips'][r] for r in roles}, 'variants': {
    name: {'mesh': variant['body_mesh'], 'clips': {r: variant['clips'][r] for r in roles}}
    for name, variant in body.get('body_variants', {}).items() if variant.get('ready')
}}
snapshot = OUT/'baseline_routes.json'
if not snapshot.exists():
    snapshot.write_text(json.dumps(baseline_routes, indent=2))
(OUT/'authored.json').write_text(json.dumps(result, separators=(',', ':')))
(OUT/'clip_metadata.json').write_text(json.dumps(metadata, separators=(',', ':')))
review = copy.deepcopy(config)
review['clips'].update(metadata)
(OUT/'review_config.json').write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT/'inventory.json').write_text(json.dumps({
    'profiles': inventory, 'types': specs, 'models': len(inventory),
    'slots': sum(len(p['slots']) for p in inventory),
    'enter_seconds': 2.8, 'idle_seconds': 4., 'exit_seconds': 3.1,
    'source': str(donor_path), 'source_sha256': hashlib.sha256(donor_path.read_bytes()).hexdigest(),
    'chair_floor_source': str(baseline_path),
    'geometry_index': 'SourceAssets/FurnitureRest20261022/RefineV2/Geometry/index.json',
    'entry_and_idle_source': 'HangingEntryV6 / RelaxedSeatV5',
    'exit_rule': 'Reverse fitted entry plus 0.3 seconds standing hold',
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('CHAIR_REUSE_SOURCE_COMPLETE', len(roles), flush=True)
