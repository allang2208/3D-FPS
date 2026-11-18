"""Fit both saved native high-bench poses to the chapel's measured wooden seat."""
import copy
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ChapelFurniture20261116'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
native = read(OUT / 'native_sources.json')
geometry = read(OUT / 'pew_geometry.json')
height = round(float(np.median([p['z'] for p in geometry['top_surfaces_cm']
                                if -18 <= p['x'] <= 0 and p['normal_z'] > .98])) * 1.25, 3)
changed = ['pelvis'] + [b + '_' + s for s in ('l', 'r')
                       for b in ('thigh', 'calf', 'foot', 'upperarm', 'lowerarm', 'hand')]


def smooth(t):
    t = float(np.clip(t, 0, 1))
    return t * t * (3 - 2 * t)


def unit(v):
    return v / max(np.linalg.norm(v), 1e-9)


def between(a, b):
    a, b = unit(a), unit(b)
    v = np.cross(a, b)
    angle = np.arctan2(np.linalg.norm(v), np.dot(a, b))
    return R.from_rotvec(unit(v) * angle).as_matrix()


result = {'variants': {}, 'changed_bones': changed, 'surface_height': height,
          'anchor_x_cm': -18, 'seat_spacing_cm': 87.5, 'source_kind': 'Chair55'}
for variant, rig in native.items():
    ix = {n: i for i, n in enumerate(rig['names'])}
    parents = rig['parents']

    def fk(f):
        w = np.tile(np.eye(4), (len(f), 1, 1))
        w[:, :3, :3] = R.from_quat(f[:, 3:7]).as_matrix() * f[:, None, 7:]
        w[:, :3, 3] = f[:, :3]
        for i, p in enumerate(parents):
            if p >= 0:
                w[i] = w[p] @ w[i]
        return w

    def rotate(f, i, world):
        p = parents[i]
        f[i, 3:7] = R.from_matrix(fk(f)[p, :3, :3].T @ world if p >= 0 else world).as_quat()

    def solve(f, chain, target, pole):
        a, b, c = [ix[n] for n in chain]
        w = fk(f)
        h, k, e = w[[a, b, c], :3, 3]
        l1, l2 = np.linalg.norm(k - h), np.linalg.norm(e - k)
        distance = np.clip(np.linalg.norm(target - h), abs(l1 - l2) + .05, l1 + l2 - .1)
        direction = unit(target - h)
        bend = unit(pole - h - direction * np.dot(pole - h, direction))
        along = (l1 * l1 + distance * distance - l2 * l2) / (2 * distance)
        knee = h + direction * along + bend * np.sqrt(max(0, l1 * l1 - along * along))
        end = h + direction * distance
        rotate(f, a, between(k - h, knee - h) @ w[a, :3, :3])
        w = fk(f)
        rotate(f, b, between(w[c, :3, 3] - w[b, :3, 3], end - w[b, :3, 3]) @ w[b, :3, :3])

    standing = fk(np.asarray(rig['clips']['Enter']['frames'][0]))
    settled = fk(np.asarray(rig['clips']['Idle']['frames'][0]))

    def fit(frame, weight):
        f = np.asarray(frame).copy()
        old = fk(f)
        # The pew is 54.56 cm high, not the donor's 55 cm. Move the seated pelvis,
        # retain the standing endpoints and solve contacts without stretching bones.
        f[ix['pelvis'], 2] += (height - 55) * weight
        for side in ('l', 'r'):
            thigh, calf, foot = [ix[b + '_' + side] for b in ('thigh', 'calf', 'foot')]
            target = settled[foot, :3, 3].copy()
            target[1] -= 7.8
            target[2] = standing[foot, 2, 3]
            target = old[foot, :3, 3] * (1 - weight) + target * weight
            pole = old[calf, :3, 3].copy()
            solve(f, [b + '_' + side for b in ('thigh', 'calf', 'foot')], target, pole)
            flat = Slerp([0, 1], R.from_matrix(np.asarray([old[foot, :3, :3], standing[foot, :3, :3]])))(weight).as_matrix()
            rotate(f, foot, flat)
            new = fk(f)
            # Preserve the donor's palm-to-thigh relationship as the knees lower.
            contact_shift = ((new[thigh, :3, 3] * .45 + new[calf, :3, 3] * .55)
                             - (old[thigh, :3, 3] * .45 + old[calf, :3, 3] * .55))
            hand, elbow = ix['hand_' + side], ix['lowerarm_' + side]
            solve(f, [b + '_' + side for b in ('upperarm', 'lowerarm', 'hand')],
                  old[hand, :3, 3] + contact_shift,
                  old[elbow, :3, 3] + contact_shift * .5)
            rotate(f, hand, old[hand, :3, :3])
        return f.tolist()

    fitted = copy.deepcopy(rig)
    for phase, take in fitted['clips'].items():
        frames = []
        for i, frame in enumerate(take['frames']):
            t = i / take['rate']
            if phase == 'Exit':
                t = max(0, rig['clips']['Enter']['duration'] - t)
            weight = 1 if phase == 'Idle' else smooth((t - 1.15) / .9)
            frames.append(fit(frame, weight) if weight > 0 else frame)
        take['frames'] = frames
    # Join exact native endpoints while keeping the existing breathing loop.
    entry_end = fitted['clips']['Enter']['frames'][-1]
    fitted['clips']['Idle']['frames'][0] = copy.deepcopy(entry_end)
    fitted['clips']['Idle']['frames'][-1] = copy.deepcopy(entry_end)
    fitted['clips']['Exit']['frames'][0] = copy.deepcopy(entry_end)
    if variant == 'default':
        bind = fk(np.asarray(rig['reference']))
        fitted['eye_offset'] = (bind[ix['head'], :3, :3].T @ np.array([0., 7., 6.])).tolist()
    else:
        g = ROOT / 'SourceAssets/KaitlinPlayer20261023/NativeGeometry'
        bones = read(g / 'MHC_Kaitlin_Body.json')['bones']
        head = next(b for b in bones if b['name'] == 'head')
        eyes = [b['position'] for b in read(g / 'SKM_MHC_Kaitlin_FaceMesh.json')['bones']
                if b['name'] in ('FACIAL_L_Eye', 'FACIAL_R_Eye')]
        fitted['eye_offset'] = (np.asarray(head['axes']) @ (np.mean(eyes, axis=0) - np.asarray(head['position']))).tolist()
    result['variants'][variant] = fitted
    print('CHAPEL_PEW_AUTHORED', variant, height, flush=True)
(OUT / 'authored.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
