"""Native relaxed arms beside the body, with fingertip clearance above the pew."""
import copy
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'SourceAssets/ChapelFurniture20261116'
OUT = BASE / 'HangingHandsR3'
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
prior = read(BASE / 'HandsR2/authored.json')
sources = read(BASE / 'HandsR2/native_sources.json')
body = read(ROOT / 'Content/ColdSteelData/player_body.json')
DIGITS = ('thumb', 'index', 'middle', 'ring', 'pinky')
changed = prior['changed_bones']


def unit(v):
    return v / max(np.linalg.norm(v), 1e-10)


def smooth(t):
    t = float(np.clip(t, 0, 1))
    return t*t*t*(10 - 15*t + 6*t*t)


def blend(a, b, t):
    return Slerp([0, 1], R.from_matrix(np.asarray([a, b])))(float(np.clip(t, 0, 1))).as_matrix()


def between(a, b):
    a, b = unit(a), unit(b)
    v = np.cross(a, b)
    return R.from_rotvec(unit(v) * math.atan2(np.linalg.norm(v), np.dot(a, b))).as_matrix()


def basis(forward, normal):
    y = unit(forward)
    z = unit(normal-y*np.dot(normal, y))
    return np.column_stack((np.cross(y, z), y, z))


def transforms(values):
    f = np.asarray(values)
    m = np.tile(np.eye(4), (len(f), 1, 1))
    m[:, :3, :3] = R.from_quat(f[:, 3:7]).as_matrix()*f[:, None, 7:]
    m[:, :3, 3] = f[:, :3]
    return m


def unpack(m):
    scale = np.linalg.norm(m[:, :3, :3], axis=1)
    return np.concatenate((m[:, :3, 3], R.from_matrix(m[:, :3, :3]/scale[:, None, :]).as_quat(), scale), axis=1)


result = {'variants': {}, 'changed_bones': changed, 'surface_height': prior['surface_height'],
          'source_kind': 'ChapelPewHandsR2', 'reference_kind': 'Sofa.Enter hanging arms',
          'revision': 'ChapelPewHangingHandsR3_20261116'}
for variant, old_rig in prior['variants'].items():
    rig = copy.deepcopy(old_rig)
    node = body if variant == 'default' else body['body_variants'][variant]
    saved = read(BASE / 'HandsR2/Preview' / variant / 'saved_poses.json')
    if rig['mesh'] != node['body_mesh'] or rig['names'] != saved['names']:
        raise RuntimeError('Refresh native body inputs: ' + variant)
    names, parents = rig['names'], rig['parents']
    ix = {n: i for i, n in enumerate(names)}
    for phase, take in rig['clips'].items():
        native = saved['clips'][phase]
        if native['asset'] != node['clips']['Rest.ChapelPew.' + phase]:
            raise RuntimeError('Pew route changed since saved capture: ' + variant + '/' + phase)
        take['asset'] = native['asset']
        frames = []
        for pose in native['world']:
            w = transforms(pose)
            local = w.copy()
            for i, parent in enumerate(parents):
                if parent >= 0:
                    local[i] = np.linalg.inv(w[parent]) @ w[i]
            frames.append(unpack(local).tolist())
        take['frames'] = frames
    geo = read(BASE / 'HandsR2/Preview' / variant / 'body.json')
    points = np.asarray(geo['positions'])
    bind = transforms([b['bind'] for b in geo['bones']])
    inverse_bind = np.linalg.inv(bind)
    gix = {b['name']: i for i, b in enumerate(geo['bones'])}
    dominant = [geo['bones'][max(w, key=lambda p: p[1])[0]]['name'] for w in geo['weights']]
    groups = {}
    for side in ('l', 'r'):
        selected = [i for i, n in enumerate(dominant) if n.endswith('_'+side)
                    and (n.startswith('hand_') or any(n.startswith(d+'_') for d in DIGITS))]
        rows = {}
        for out_index, vertex in enumerate(selected):
            for bone, weight in geo['weights'][vertex]:
                rows.setdefault(bone, []).append((out_index, vertex, weight))
        groups[side] = (len(selected), [(ix[geo['bones'][b]['name']], inverse_bind[b],
                            np.asarray(v)[:, 0].astype(int), np.asarray(v)[:, 1].astype(int),
                            np.asarray(v)[:, 2, None]) for b, v in rows.items()])

    def fk(f):
        w = transforms(f)
        for i, parent in enumerate(parents):
            if parent >= 0:
                w[i] = w[parent] @ w[i]
        return w

    def hand_skin(w, side):
        count, rows = groups[side]
        value = np.zeros((count, 3))
        for index, inverse, ids, verts, weights in rows:
            m = w[index] @ inverse
            value[ids] += (points[verts] @ m[:3, :3].T+m[:3, 3])*weights
        return value

    def rotate(f, index, world_rotation):
        parent = parents[index]
        rot = fk(f)[parent, :3, :3] if parent >= 0 else np.eye(3)
        f[index, 3:7] = R.from_matrix(rot.T @ world_rotation).as_quat()

    def solve_arm(f, side, target, pole):
        a, b, c = [ix[n+'_'+side] for n in ('upperarm', 'lowerarm', 'hand')]
        w = fk(f)
        h, k, end = w[[a, b, c], :3, 3]
        l1, l2 = np.linalg.norm(k-h), np.linalg.norm(end-k)
        distance = np.clip(np.linalg.norm(target-h), abs(l1-l2)+.1, l1+l2-.3)
        direction = unit(target-h)
        bend = unit(pole-h-direction*np.dot(pole-h, direction))
        along = (l1*l1+distance*distance-l2*l2)/(2*distance)
        elbow = h+direction*along+bend*math.sqrt(max(0, l1*l1-along*along))
        rotate(f, a, between(k-h, elbow-h) @ w[a, :3, :3])
        w = fk(f)
        rotate(f, b, between(w[c, :3, 3]-w[b, :3, 3], h+direction*distance-w[b, :3, 3]) @ w[b, :3, :3])

    donor = sources[variant]['references']['Enter']
    donor_idle = fk(np.asarray(sources[variant]['references']['Idle']['frames'][0]))
    hand_basis = {}
    for side in ('l', 'r'):
        hand = gix['hand_'+side]
        p = lambda n: bind[gix[n+'_'+side], :3, 3]
        forward = unit(p('middle_01')-p('hand'))
        normal = unit(np.cross(p('index_01')-p('pinky_01'), forward))
        normal = bind[hand, :3, :3].T @ normal
        if (donor_idle[ix['hand_'+side], :3, :3] @ normal)[2] > 0:
            normal *= -1
        hand_basis[side] = basis(bind[hand, :3, :3].T @ forward, normal)

    def fit(frame, phase, t):
        f = np.asarray(frame).copy()
        clock = min(.55, t*.27) if phase == 'Enter' else (max(0., min(.55, (3.1-t)*.27)) if phase == 'Exit' else .55)
        hang = np.asarray(donor['frames'][round(clock*donor['rate'])])
        weight = smooth((t-.3)/1.35) if phase == 'Enter' else (1-smooth((t-.9)/1.55) if phase == 'Exit' else 1.)
        for name in changed:
            f[ix[name], 3:7] = hang[ix[name], 3:7]
        for side, sign in (('l', 1), ('r', -1)):
            w = fk(f)
            arm, forearm, hand = [ix[n+'_'+side] for n in ('upperarm', 'lowerarm', 'hand')]
            shoulder = w[arm, :3, 3]
            length = np.linalg.norm(w[forearm, :3, 3]-shoulder)+np.linalg.norm(w[hand, :3, 3]-w[forearm, :3, 3])
            desired = basis([sign*.035, .045, -1.], [-sign, -.08, 0.]) @ hand_basis[side].T
            hand_rotation = blend(w[hand, :3, :3], desired, weight)
            wrist = w[hand, :3, 3].copy()
            target = shoulder+np.array([sign*12.5, 6.5 if side == 'l' else 7.5, -length*.94])
            wrist = wrist*(1-weight)+target*weight
            rotate(f, hand, hand_rotation)
            oriented = fk(f)
            hand_points = hand_skin(oriented, side)
            minimum = float(np.min(hand_points[:, 2]-oriented[hand, 2, 3]))
            floor = prior['surface_height']+1.2-minimum
            # The bench is continuous beside the hips: bend the elbow softly enough
            # for lowered fingertips to clear its surface, without reaching onto a thigh.
            seat_weight = smooth((17.-wrist[1])/12.)
            z = .5*(wrist[2]+floor+math.sqrt((wrist[2]-floor)**2+.45**2))
            wrist[2] += (z-wrist[2])*seat_weight
            pole = shoulder+np.array([sign*8., -11., -25.])
            solve_arm(f, side, wrist, pole)
            rotate(f, hand, hand_rotation)
        return f.tolist()

    for phase, take in rig['clips'].items():
        take['frames'] = [fit(frame, phase, i/take['rate']) for i, frame in enumerate(take['frames'])]
        print('CHAPEL_HANGING_AUTHORED', variant, phase, flush=True)
    for phase, index, other, source_index in (('Idle', 0, 'Enter', -1), ('Idle', -1, 'Enter', -1),
                                              ('Exit', 0, 'Enter', -1), ('Exit', -1, 'Enter', 0)):
        for name in changed:
            i = ix[name]
            rig['clips'][phase]['frames'][index][i] = copy.deepcopy(rig['clips'][other]['frames'][source_index][i])
    result['variants'][variant] = rig
(OUT/'authored.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
(OUT/'reference_routes.json').write_text(json.dumps({v:s['references']['Enter']['asset'] for v,s in sources.items()}, indent=2), encoding='utf-8')
print('CHAPEL_HANGING_AUTHORING_COMPLETE', flush=True)
