"""Native sofa timing plus real thigh/palm contacts for relaxed chapel seating."""
import copy
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'SourceAssets/ChapelFurniture20261116'
OUT = BASE / 'HandsR2'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sources = read(OUT / 'native_sources.json')
prior = read(BASE / 'authored.json')
DIGITS = ('thumb', 'index', 'middle', 'ring', 'pinky')
changed = [n + '_' + s for s in ('l', 'r') for n in ('clavicle', 'upperarm', 'lowerarm', 'hand')]
changed += [f'{d}_{j:02d}_{s}' for s in ('l', 'r') for d in DIGITS for j in (1, 2, 3)]


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
    z = unit(normal - y * np.dot(normal, y))
    return np.column_stack((np.cross(y, z), y, z))


def transforms(values):
    f = np.asarray(values)
    m = np.tile(np.eye(4), (len(f), 1, 1))
    m[:, :3, :3] = R.from_quat(f[:, 3:7]).as_matrix() * f[:, None, 7:]
    m[:, :3, 3] = f[:, :3]
    return m


result = {'variants': {}, 'changed_bones': changed, 'surface_height': prior['surface_height'],
          'source_kind': 'ChapelPew', 'reference_kind': 'Sofa', 'revision': 'ChapelPewHandsR2_20261116'}
for variant, rig in sources.items():
    ix = {name: i for i, name in enumerate(rig['names'])}
    parents = rig['parents']
    geo = read(BASE / 'PreviewR1' / variant / 'body.json')
    if geo['source'] != rig['mesh']:
        raise RuntimeError('Read the new body geometry before fitting: ' + variant)
    points = np.asarray(geo['positions'])
    tris = np.asarray(geo['triangles'], dtype=int)
    gix = {b['name']: i for i, b in enumerate(geo['bones'])}
    bind = transforms([b['bind'] for b in geo['bones']])
    inverse_bind = np.linalg.inv(bind)
    rows = {}
    dominant = []
    for i, weights in enumerate(geo['weights']):
        dominant.append(geo['bones'][max(weights, key=lambda p: p[1])[0]]['name'])
        for bone, weight in weights:
            rows.setdefault(bone, []).append((i, weight))
    skin_groups = [(ix[geo['bones'][bone]['name']], inverse_bind[bone],
                    np.asarray(values)[:, 0].astype(int), np.asarray(values)[:, 1, None])
                   for bone, values in rows.items()]
    thigh_faces = {}
    for side in ('l', 'r'):
        mask = np.array([n.startswith('thigh') and n.endswith('_' + side) for n in dominant])
        thigh_faces[side] = tris[mask[tris].sum(axis=1) >= 2]

    def fk(f):
        w = transforms(f)
        for i, parent in enumerate(parents):
            if parent >= 0:
                w[i] = w[parent] @ w[i]
        return w

    def skin(world):
        value = np.zeros_like(points)
        for index, inverse, ids, weights in skin_groups:
            m = world[index] @ inverse
            value[ids] += (points[ids] @ m[:3, :3].T + m[:3, 3]) * weights
        return value

    def rotate(f, index, world_rotation):
        parent = parents[index]
        parent_rotation = fk(f)[parent, :3, :3] if parent >= 0 else np.eye(3)
        f[index, 3:7] = R.from_matrix(parent_rotation.T @ world_rotation).as_quat()

    def solve_arm(f, side, target, pole):
        a, b, c = [ix[n + '_' + side] for n in ('upperarm', 'lowerarm', 'hand')]
        w = fk(f)
        h, k, end = w[[a, b, c], :3, 3]
        l1, l2 = np.linalg.norm(k-h), np.linalg.norm(end-k)
        distance = np.clip(np.linalg.norm(target-h), abs(l1-l2)+.1, l1+l2-.3)
        direction = unit(target-h)
        bend = unit(pole-h-direction*np.dot(pole-h, direction))
        along = (l1*l1+distance*distance-l2*l2)/(2*distance)
        elbow = h+direction*along+bend*math.sqrt(max(0, l1*l1-along*along))
        end = h+direction*distance
        rotate(f, a, between(k-h, elbow-h) @ w[a, :3, :3])
        w = fk(f)
        rotate(f, b, between(w[c, :3, 3]-w[b, :3, 3], end-w[b, :3, 3]) @ w[b, :3, :3])

    def sample(take, time):
        x = float(np.clip(time * take['rate'], 0, len(take['frames']) - 1))
        i = min(int(x), len(take['frames'])-2)
        a, b = np.asarray(take['frames'][i]), np.asarray(take['frames'][i+1])
        t = x-i
        f = a*(1-t)+b*t
        q = b[:, 3:7].copy()
        q[(a[:, 3:7]*q).sum(axis=1) < 0] *= -1
        f[:, 3:7] = a[:, 3:7]*(1-t)+q*t
        f[:, 3:7] /= np.linalg.norm(f[:, 3:7], axis=1)[:, None]
        return f

    donor_idle = fk(sample(rig['references']['Idle'], 0))
    palm_basis, palm_offset = {}, {}
    for side in ('l', 'r'):
        hand = gix['hand_' + side]
        p = lambda name: bind[gix[name + '_' + side], :3, 3]
        forward = unit(p('middle_01') - p('hand'))
        normal = unit(np.cross(p('index_01')-p('pinky_01'), forward))
        local_forward = bind[hand, :3, :3].T @ forward
        local_normal = bind[hand, :3, :3].T @ normal
        if (donor_idle[ix['hand_' + side], :3, :3] @ local_normal)[2] > 0:
            normal *= -1
            local_normal *= -1
        palm_basis[side] = basis(local_forward, local_normal)
        ids = np.array([i for i, n in enumerate(dominant) if n == 'hand_' + side])
        relative = points[ids] - p('hand')
        along = relative @ forward
        across = relative @ np.cross(forward, normal)
        length = np.linalg.norm(p('middle_01') - p('hand'))
        center = (along > length*.20) & (along < length*.76) & (np.abs(across) < 2.1)
        palm = ids[center]
        if len(palm) < 4:
            raise RuntimeError('Palm skin landmark missing: ' + variant + '/' + side)
        outward = (points[palm]-p('hand')) @ normal
        palm = palm[outward >= np.quantile(outward, .58)]
        palm_offset[side] = bind[hand, :3, :3].T @ (points[palm].mean(axis=0) - p('hand'))

    def surface(vertices, side, origin, direction):
        tri = vertices[thigh_faces[side]]
        e1, e2 = tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]
        h = np.cross(np.broadcast_to(direction, e2.shape), e2)
        a = np.einsum('ij,ij->i', e1, h)
        valid = np.abs(a) > 1e-8
        inv = np.divide(1., a, out=np.zeros_like(a), where=valid)
        delta = origin-tri[:, 0]
        u = inv*np.einsum('ij,ij->i', delta, h)
        q = np.cross(delta, e1)
        v = inv*(q @ direction)
        t = inv*np.einsum('ij,ij->i', e2, q)
        valid &= (u >= 0) & (v >= 0) & (u+v <= 1) & (t >= 0)
        hits = np.flatnonzero(valid)
        if not len(hits):
            raise RuntimeError('Cannot place palm on thigh: ' + variant + '/' + side)
        index = hits[np.argmin(t[hits])]
        normal = unit(np.cross(e1[index], e2[index]))
        if np.dot(normal, -direction) < 0:
            normal *= -1
        return origin + direction*t[index], normal

    def fit(frame, phase, time):
        f = np.asarray(frame).copy()
        old = fk(f)
        skin_points = skin(old)
        if phase == 'Enter':
            hang_time = min(time*.27, .55)
        elif phase == 'Exit':
            hang_time = max(0, min(.55, (2.8-time)*.27))
        else:
            hang_time = .55
        hang = sample(rig['references']['Enter'], hang_time)
        rest = sample(rig['references']['Idle'], time if phase == 'Idle' else 0)
        for side, sign in (('l', 1), ('r', -1)):
            if phase == 'Enter':
                start, finish = ((.72, 2.32) if side == 'l' else (.92, 2.55))
                weight = smooth((time-start)/(finish-start))
            elif phase == 'Exit':
                start, finish = ((.60, 2.18) if side == 'l' else (.76, 2.36))
                weight = 1-smooth((time-start)/(finish-start))
            else:
                weight = 1.
            for name in changed:
                if name.endswith('_' + side):
                    i = ix[name]
                    f[i, 3:7] = hang[i, 3:7]
            cl = ix['clavicle_' + side]
            f[cl, 3:7] = R.from_matrix(blend(R.from_quat(hang[cl, 3:7]).as_matrix(),
                                           R.from_quat(rest[cl, 3:7]).as_matrix(), weight)).as_quat()
            w = fk(f)
            hip, knee = old[[ix['thigh_'+side], ix['calf_'+side]], :3, 3]
            along = unit(knee-hip)
            up = unit(np.array([0., 0., 1.])-along*along[2])
            fraction = .38 if side == 'l' else .46
            if phase == 'Exit':
                fraction += .035*smooth(time/.65)*weight
            location, normal = surface(skin_points, side, hip+(knee-hip)*fraction+up*25, -up)
            # The torso is unchanged. Palms follow the measured quadriceps slope.
            forward = unit(along + np.array([-sign*.075, 0, 0]))
            desired = basis(forward, -up) @ palm_basis[side].T
            target = location + up*.18 - desired @ palm_offset[side]
            if phase == 'Exit':
                target += up*(1.8*smooth((time-.25)/.6)*(1-weight))
            hand = ix['hand_' + side]
            wrist = w[hand, :3, 3]*(1-weight) + target*weight
            arc = math.sin(math.pi*weight)
            wrist += np.array([sign*3.5, 2., 5.]) * arc
            # Let hanging hands clear the seat's front edge while the pelvis lowers/rises.
            clearance = smooth((76-wrist[2])/22)*(1-weight)
            wrist[1] += max(0., 19.-wrist[1])*clearance
            shoulder = w[ix['upperarm_' + side], :3, 3]
            pole = w[ix['lowerarm_' + side], :3, 3]*(1-weight) + (shoulder+np.array([sign*12., -12., -28.]))*weight
            solve_arm(f, side, wrist, pole)
            turn_weight = smooth((weight-.08)/.92)
            rotate(f, hand, blend(w[hand, :3, :3], desired, turn_weight))
            # Reuse the lap fingers, rather than the opened armrest fingers used by R1.
            for digit in DIGITS:
                delay = .08 if digit in ('ring', 'pinky') else .02
                finger_weight = smooth((weight-delay)/(1-delay))
                for joint in (1, 2, 3):
                    i = ix[f'{digit}_{joint:02d}_{side}']
                    f[i, 3:7] = R.from_matrix(blend(R.from_quat(hang[i, 3:7]).as_matrix(),
                                                   R.from_quat(rest[i, 3:7]).as_matrix(), finger_weight)).as_quat()
            # Close the fan slightly, with a separate amount for each outer finger.
            fw = fk(f)
            middle = unit(fw[ix['middle_02_' + side], :3, 3]-fw[ix['middle_01_' + side], :3, 3])
            for digit, amount in (('index', .30), ('ring', .25), ('pinky', .38)):
                i, j = ix[digit+'_01_'+side], ix[digit+'_02_'+side]
                direction = unit(fw[j, :3, 3]-fw[i, :3, 3])
                wanted = unit(direction*(1-amount*weight)+middle*amount*weight)
                rotate(f, i, between(direction, wanted) @ fw[i, :3, :3])
        return f.tolist()

    fitted = {k: copy.deepcopy(v) for k, v in rig.items() if k != 'references'}
    fitted['eye_offset'] = prior['variants'][variant]['eye_offset']
    for phase, take in fitted['clips'].items():
        take['frames'] = [fit(frame, phase, i/take['rate']) for i, frame in enumerate(take['frames'])]
        print('CHAPEL_RELAXED_HANDS_AUTHORED', variant, phase, flush=True)
    for phase, index, source_phase, source_index in (
            ('Idle', 0, 'Enter', -1), ('Idle', -1, 'Enter', -1), ('Exit', 0, 'Enter', -1),
            ('Exit', -1, 'Enter', 0)):
        for name in changed:
            i = ix[name]
            fitted['clips'][phase]['frames'][index][i] = copy.deepcopy(fitted['clips'][source_phase]['frames'][source_index][i])
    result['variants'][variant] = fitted
(OUT / 'authored.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
(OUT / 'reference_routes.json').write_text(json.dumps({k: {p: t['asset'] for p, t in v['references'].items()}
                                                     for k, v in sources.items()}, indent=2), encoding='utf-8')
print('CHAPEL_RELAXED_HANDS_COMPLETE', flush=True)
