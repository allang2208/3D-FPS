"""Release both armrests before standing, with continuous outward elbow planes."""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'SourceAssets/FurnitureRest20261022/ChairReuse20261024'
OUT = ROOT/'SourceAssets/FurnitureRest20261022/ArmrestExit20261024'
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
ns = {'__file__': str(ROOT/'Tools/FurnitureRest/refine.py')}
exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0], ns)
fk, rot, ik, handrot, ix, ref, bind = [ns[k] for k in ('fk', 'rot', 'ik', 'handrot', 'ix', 'ref', 'bind')]

def blendrot(a, b, t):
    return Slerp([0, 1], R.from_matrix(np.array([a, b])))(float(np.clip(t, 0, 1))).as_matrix()


tree = ast.parse((ROOT/'Tools/FurnitureRest/hanging_entry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name in ('smooth', 'hanging')], type_ignores=[]), 'hanging_entry.py', 'exec'))
source = read(BASE/'authored.json')
kinds = ('Chair50', 'Chair52')
data = {k: source[k] for k in ('mesh', 'skeleton', 'names', 'parents', 'reference')}
data['clips'] = {r: copy.deepcopy(take) for r, take in source['clips'].items() if r.split('.')[1] in kinds}
data['changed_roles'] = [f'Rest.{kind}.Exit' for kind in kinds]
arm_ids = []
for i, name in enumerate(data['names']):
    ancestor = i
    while ancestor >= 0:
        if data['names'][ancestor].startswith('clavicle_'):
            arm_ids.append(i)
            break
        ancestor = data['parents'][ancestor]

def unit(v):
    return v / max(np.linalg.norm(v), 1e-9)


def basis(direction, normal):
    y = unit(direction)
    z = unit(normal-y*(normal@y))
    return np.column_stack((np.cross(y, z), y, z))


records = {}
for kind in kinds:
    role = f'Rest.{kind}.Exit'
    take = source['clips'][role]
    first = np.array(take['frames'][0])
    start = fk(first)
    reference = {}
    for side, sign in (('l', 1), ('r', -1)):
        a, b, c = [ix[n+'_'+side] for n in ('upperarm', 'lowerarm', 'hand')]
        shoulder, elbow, wrist = start[[a, b, c], :3, 3]
        normal = unit(np.cross(elbow-shoulder, wrist-elbow))
        across = unit(start[ix['index_01_'+side], :3, 3]-start[ix['pinky_01_'+side], :3, 3])
        reference[side] = {'ids': (a, b, c), 'l1': np.linalg.norm(elbow-shoulder),
                           'l2': np.linalg.norm(wrist-elbow), 'upper_basis': basis(elbow-shoulder, normal),
                           'lower_basis': basis(wrist-elbow, normal), 'pole': unit(elbow-shoulder),
                           'across': across, 'last_plane_angle': 0.}
    frames = []
    samples = []
    for j, frame in enumerate(take['frames']):
        t = j/take['rate']
        original = np.array(frame)
        f = original.copy()
        row = {'time': t, 'arms': {}}
        for side, sign in (('l', 1), ('r', -1)):
            entry = reference[side]
            a, b, c = entry['ids']
            hang = hanging(original, side, sign, t, 'Exit')
            hw = fk(hang)
            h0 = start[c, :3, 3]
            delay = .06 if side == 'r' else 0.
            lift = smooth((t-.50-delay)/.35)
            advance = smooth((t-.85-delay)/.70)
            release = smooth((t-1.55-delay)/.85)
            lifted = h0 + [0., 4., 7.]
            clear = np.array([sign*(27. if kind == 'Chair50' else 29.), 24., h0[2]+11.])
            target = h0*(1-lift)+lifted*lift
            target = target*(1-advance)+clear*advance
            target = target*(1-release)+hw[c, :3, 3]*release
            wrist_turn = smooth((t-1.30-delay)/.95)
            hand_rotation = blendrot(start[c, :3, :3], hw[c, :3, :3], wrist_turn)
            w = fk(f)
            shoulder = w[a, :3, 3]
            direction = unit(target-shoulder)
            distance = np.clip(np.linalg.norm(target-shoulder), abs(entry['l1']-entry['l2'])+.1,
                               (entry['l1']+entry['l2'])*.98)
            pole = unit(entry['pole']*(1-smooth(t/.7)) + unit(np.array([sign*35., -10., -18.]))*smooth(t/.7))
            recover_plane = smooth((t-1.15-delay)/1.25)
            bend_start = unit(pole-direction*(pole@direction))
            hang_pole=hw[b,:3,3]-hw[a,:3,3]
            hang_direction=unit(hw[c,:3,3]-hw[a,:3,3])
            hang_bend=unit(hang_pole-hang_direction*(hang_pole@hang_direction))
            bend_end=ns['between'](hang_direction,direction)@hang_bend
            # Interpolate on the elbow circle. Blending raw pole points can
            # collapse their projection onto the arm axis and flip the elbow.
            plane_angle=math.atan2(direction@np.cross(bend_start,bend_end),bend_start@bend_end)
            plane_angle+=round((entry['last_plane_angle']-plane_angle)/(2*math.pi))*2*math.pi
            entry['last_plane_angle']=plane_angle
            bend=R.from_rotvec(direction*plane_angle*recover_plane).as_matrix()@bend_start
            along = (entry['l1']**2+distance**2-entry['l2']**2)/(2*distance)
            elbow = shoulder+direction*along+bend*math.sqrt(max(0., entry['l1']**2-along**2))
            wrist = shoulder+direction*distance
            normal = unit(np.cross(elbow-shoulder, wrist-elbow))
            # Both endpoint frames preserve the native bone axes. Blend their
            # axial orientation as the palm turns, instead of accumulating
            # shortest-arc rotations or concentrating twist at the wrist.
            hang_upper=hw[b,:3,3]-hw[a,:3,3]
            hang_lower=hw[c,:3,3]-hw[b,:3,3]
            hang_normal=unit(np.cross(hang_upper,hang_lower))
            return_basis=smooth((t-1.45-delay)/.95)
            upper_correction=blendrot(entry['upper_basis'].T@start[a,:3,:3],
                                     basis(hang_upper,hang_normal).T@hw[a,:3,:3],return_basis)
            lower_correction=blendrot(entry['lower_basis'].T@start[b,:3,:3],
                                     basis(hang_lower,hang_normal).T@hw[b,:3,:3],return_basis)
            upper = basis(elbow-shoulder, normal) @ upper_correction
            lower = basis(wrist-elbow, normal) @ lower_correction
            rot(f, a, upper)
            rot(f, b, lower)
            rot(f, c, hand_rotation)
            for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                for joint in (1, 2, 3):
                    bone = ix[f'{digit}_{joint:02d}_{side}']
                    amount = smooth((t-1.45-delay)/.90)
                    f[bone, 3:7] = R.from_matrix(blendrot(R.from_quat(first[bone, 3:7]).as_matrix(),
                                                        R.from_quat(hang[bone, 3:7]).as_matrix(), amount)).as_quat()
            row['arms'][side] = {'hand_target': target.tolist(), 'native_roll_return': return_basis,
                                 'requested_reach': float(np.linalg.norm(target-shoulder)/(entry['l1']+entry['l2']))}
        # The clear, standing handoff returns exactly to the existing posture.
        finish = smooth((t-2.30)/.50)
        for bone in arm_ids:
            f[bone, 3:7] = R.from_matrix(blendrot(R.from_quat(f[bone, 3:7]).as_matrix(),
                                                R.from_quat(original[bone, 3:7]).as_matrix(), finish)).as_quat()
        if j == 0 or t >= 2.8:
            f = original
        frames.append(f.tolist())
        samples.append(row)
    data['clips'][role]['frames'] = frames
    records[kind] = samples
    print('ARMREST_EXIT_AUTHORED', kind, flush=True)

body = read(ROOT/'Content/ColdSteelData/player_body.json')
roles = data['changed_roles']
snapshot = OUT/'baseline_routes.json'
if not snapshot.exists():
    snapshot.write_text(json.dumps({'default': {r: body['clips'][r] for r in roles}, 'variants': {
        name: {'mesh': v['body_mesh'], 'clips': {r: v['clips'][r] for r in roles}}
        for name, v in body.get('body_variants', {}).items() if v.get('ready')
    }}, indent=2))
cfg = read(ROOT/'Content/ColdSteelData/furniture_rest.json')
(OUT/'authored.json').write_text(json.dumps(data, separators=(',', ':')))
(OUT/'clip_metadata.json').write_text(json.dumps({r: cfg['clips'][r] for r in roles}, separators=(',', ':')))
(OUT/'review_config.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT/'arm_paths.json').write_text(json.dumps(records, indent=2))
(OUT/'source_revision.json').write_text(json.dumps({'source': str(BASE/'authored.json'),
    'source_sha256': hashlib.sha256((BASE/'authored.json').read_bytes()).hexdigest(),
    'changed_roles': roles, 'body_legs_head_timing_unchanged': True}, indent=2))
