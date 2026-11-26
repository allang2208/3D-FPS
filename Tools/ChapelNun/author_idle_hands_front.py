"""Author a native nun idle from the user's clasped-hands still reference.

This is newly authored motion, not a downloaded or retargeted Cosindra clip.
Surface constraints are part of authoring: hands stay together while the upper
body breathes, and the actual long-sleeve mesh determines the elbow clearance.
"""
import json
import math
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[2]
NUN = ROOT / 'SourceAssets/ChapelNun20261115'
OUT = NUN / 'IdleHandsFrontR1'
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
rig = read(OUT / 'native_rig.json')
names, parents = rig['names'], rig['parents']
ix = {n: i for i, n in enumerate(names)}
reference = np.asarray(rig['reference'], dtype=float)
DIGITS = ('index', 'middle', 'ring', 'pinky')


def unit(v):
    return np.asarray(v, dtype=float) / max(np.linalg.norm(v), 1e-10)


def rotation(axis, degrees):
    return R.from_rotvec(unit(axis) * math.radians(degrees)).as_matrix()


def matrices(f):
    w = np.tile(np.eye(4), (len(f), 1, 1))
    w[:, :3, :3] = R.from_quat(f[:, 3:7]).as_matrix() * f[:, None, 7:]
    w[:, :3, 3] = f[:, :3]
    return w


def fk(f):
    w = matrices(f)
    for i, p in enumerate(parents):
        if p >= 0:
            w[i] = w[p] @ w[i]
    return w


def orient(f, name, desired):
    i = ix[name]
    parent = parents[i]
    q = fk(f)[parent, :3, :3] if parent >= 0 else np.eye(3)
    f[i, 3:7] = R.from_matrix(np.linalg.solve(q, desired)).as_quat()


def rotate_world(f, name, axis, degrees):
    orient(f, name, rotation(axis, degrees) @ fk(f)[ix[name], :3, :3])


def between(a, b):
    a, b = unit(a), unit(b)
    cross = np.cross(a, b)
    if np.linalg.norm(cross) < 1e-9:
        return np.eye(3)
    return R.from_rotvec(unit(cross) * math.atan2(np.linalg.norm(cross), np.dot(a, b))).as_matrix()


def basis(forward, normal):
    y = unit(forward)
    z = unit(normal - y * np.dot(normal, y))
    return np.column_stack((np.cross(y, z), y, z))


def solve_limb(f, chain, target, pole):
    a, b, c = [ix[n] for n in chain]
    w = fk(f)
    start, knee, end = w[[a, b, c], :3, 3]
    l1, l2 = np.linalg.norm(knee - start), np.linalg.norm(end - knee)
    direction = unit(target - start)
    distance = np.clip(np.linalg.norm(target - start), abs(l1 - l2) + .01, l1 + l2 - .025)
    bend = unit(pole - start - direction * np.dot(pole - start, direction))
    along = (l1*l1 + distance*distance - l2*l2) / (2*distance)
    joint = start + direction*along + bend*math.sqrt(max(0., l1*l1 - along*along))
    orient(f, chain[0], between(knee-start, joint-start) @ w[a, :3, :3])
    w = fk(f)
    orient(f, chain[1], between(w[c, :3, 3]-w[b, :3, 3], start+direction*distance-w[b, :3, 3]) @ w[b, :3, :3])


class Surface:
    def __init__(self, path):
        self.data = read(path)
        d = self.data
        self.points = np.asarray(d['positions'])
        self.tris = np.asarray(d['triangles'], dtype=int)
        self.bind = np.tile(np.eye(4), (len(d['bones']), 1, 1))
        self.bone_names = [b['name'] for b in d['bones']]
        for i, b in enumerate(d['bones']):
            self.bind[i, :3, :3] = np.asarray(b['axes']).T
            self.bind[i, :3, 3] = b['position']
        inv = np.linalg.inv(self.bind)
        rows = {}
        self.dominant = []
        for i, weights in enumerate(d['weights']):
            self.dominant.append(self.bone_names[max(weights, key=lambda p: p[1])[0]])
            for j, weight in weights:
                rows.setdefault(j, []).append((i, weight))
        self.groups = [(ix[self.bone_names[j]], inv[j], np.asarray(v)[:, 0].astype(int), np.asarray(v)[:, 1, None]) for j, v in rows.items()]
        self.material_vertices = {}
        for mat in set(d['triangle_materials']):
            self.material_vertices[mat] = np.unique(self.tris[np.asarray(d['triangle_materials']) == mat])

    def skin(self, w):
        value = np.zeros_like(self.points)
        for index, inverse, ids, weights in self.groups:
            m = w[index] @ inverse
            value[ids] += (self.points[ids] @ m[:3, :3].T + m[:3, 3]) * weights
        return value


body = Surface(NUN / 'ProductionR1/Inputs/native_body.json')
robe = Surface(NUN / 'ProductionR1/Inputs/native_robe.json')
bind = fk(reference)
base = reference.copy()
# The existing combat idle has staggered feet and a forward carried head.
# Start this civilian pose from the native anatomical reference instead.
# No face geometry, cloth weights or player idle is modified.
for i, name in enumerate(names):
    if any(name.startswith(p) for p in ('clavicle_', 'upperarm_', 'lowerarm_', 'hand_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
        base[i] = reference[i]
    if name == 'root':
        base[i] = reference[i]

# Keep the native sole orientations and floor height while narrowing the stance.
rotate_world(base, 'spine_03', [1., 0., 0.], -.6)
standing = fk(base)
for side, sign in (('l', 1), ('r', -1)):
    foot = 'foot_' + side
    target = standing[ix[foot], :3, 3].copy()
    target[0] = sign * 8.5
    target[1] += 1.0 if side == 'r' else -1.0
    solve_limb(base, ['thigh_'+side, 'calf_'+side, foot], target,
               standing[ix['calf_'+side], :3, 3] + np.array([0., 30., 0.]))
    orient(base, foot, standing[ix[foot], :3, :3])

# Distribute the slight downward gaze over both neck joints instead of making
# a deep chin tuck. A tiny asymmetry avoids a rigid ceremonial posture.
for bone, angle in (('neck_01', -1.0), ('neck_02', -2.2), ('head', -4.2)):
    orient(base, bone, bind[ix[bone], :3, :3])
    rotate_world(base, bone, [1., 0., 0.], angle)

hand_basis, palm_normal, hand_ids, palm_ids, finger_ids = {}, {}, {}, {}, {}
for side in ('l', 'r'):
    h = ix['hand_'+side]
    p = lambda name: bind[ix[name+'_'+side], :3, 3]
    forward = unit(p('middle_01')-p('hand'))
    normal = unit(np.cross(p('index_01')-p('pinky_01'), forward))
    # The concave side of the already-curled native fingers defines the palm.
    proximal = unit(p('middle_02')-p('middle_01'))
    distal = unit(p('middle_03')-p('middle_02'))
    if np.dot(distal-proximal, normal) < 0:
        normal *= -1
    hand_basis[side] = basis(bind[h, :3, :3].T @ forward, bind[h, :3, :3].T @ normal)
    palm_normal[side] = normal
    hand_ids[side] = np.array([i for i, n in enumerate(body.dominant) if n.endswith('_'+side) and any(n.startswith(x+'_') for x in ('hand', 'thumb', *DIGITS))])
    palm_ids[side] = np.array([i for i, n in enumerate(body.dominant) if n == 'hand_'+side])
    finger_ids[side] = np.array([i for i, n in enumerate(body.dominant) if n.endswith('_'+side) and any(n.startswith(x+'_') for x in ('thumb', *DIGITS))])
    # Gentle, graded curl with no interlocking fingers; thumb stays relaxed.
    for digit, extra in zip(DIGITS, (1., 2., 3., 4.)):
        for joint, fraction in ((1, 1.), (2, .70), (3, .35)):
            name = f'{digit}_{joint:02d}_{side}'
            w = fk(base)
            sign = 1. if side == 'l' else -1.
            direction = w[ix[name], :3, 0] * sign
            curl_axis = unit(np.cross(direction, palm_normal[side]))
            rotate_world(base, name, curl_axis, extra * fraction)

# Left hand is the lower support, right hand gently rests over its back.
# Wrist targets are centimetres in the native mesh component frame (+Y front).
targets = {'l': np.array([5.8, 24.8, 96.0]), 'r': np.array([-6.2, 27.0, 99.2])}
directions = {'l': unit([-.47, .02, -.88]), 'r': unit([.64, -.015, -.77])}
rotations = {s: basis(directions[s], np.array([0., -1., -.03])) @ hand_basis[s].T for s in ('l', 'r')}
pole_width = {'l': 19.5, 'r': 20.0}


def forearm_twist(f, side):
    w = fk(f)
    forearm, hand = ix['lowerarm_'+side], ix['hand_'+side]
    # Swing and twist decomposition relative to the native wrist reference.
    wrist_delta = R.from_matrix(w[forearm, :3, :3].T @ w[hand, :3, :3] @ R.from_quat(reference[hand, 3:7]).as_matrix().T).as_quat()
    axis = unit(reference[hand, :3])
    projection = axis*np.dot(wrist_delta[:3], axis)
    tq = np.r_[projection, wrist_delta[3]]
    tq /= max(np.linalg.norm(tq), 1e-9)
    if tq[3] < 0:
        tq *= -1
    rv = R.from_quat(tq).as_rotvec()
    for suffix, amount in (('01', .72), ('02', .34)):
        name = f'lowerarm_twist_{suffix}_{side}'
        i = ix[name]
        f[i, 3:7] = (R.from_rotvec(rv*amount)*R.from_quat(reference[i, 3:7])).as_quat()


def place_hands(f, offset=None):
    offset = np.zeros(3) if offset is None else offset
    for side, sign in (('l', 1), ('r', -1)):
        solve_limb(f, ['upperarm_'+side, 'lowerarm_'+side, 'hand_'+side], targets[side]+offset,
                   np.array([sign*pole_width[side], 7., 108.]))
        orient(f, 'hand_'+side, rotations[side])
        forearm_twist(f, side)
    return f


# Fit the support hand to the actual dorsal skin surface of the lower hand.
# Offset the entire contacting pair afterwards; this preserves finger contact.
for _ in range(12):
    f = place_hands(base.copy())
    points = body.skin(fk(f))
    left = points[hand_ids['l']]
    right = points[hand_ids['r']]
    # Match all overlapping XY-plane (X,Z) surface columns, using the maximum
    # required Y offset. This prevents an apparently touching palm from hiding
    # fingers that have passed through the opposite hand.
    tree = cKDTree(left[:, [0, 2]])
    neighborhoods = tree.query_ball_point(right[:, [0, 2]], .42)
    shifts = [float(left[j, 1].max()-right[i, 1]) for i, j in enumerate(neighborhoods) if j]
    if not shifts:
        raise RuntimeError('Authored hands do not overlap; adjust contact layout')
    correction = max(shifts)+.12
    targets['r'][1] += correction
    if abs(correction) < .015:
        break

# Use long-sleeve surfaces to provide space around the pose rather than
# shrinking sleeves or hiding troublesome cloth sections.
torso_ids = np.unique(np.concatenate([robe.material_vertices[m] for m in (0, 4, 7, 10)]))
sleeve_vertices = np.unique(np.concatenate([robe.material_vertices[m] for m in (1, 2, 3)]))
sleeve_ids = {s: np.array([i for i in sleeve_vertices if robe.dominant[i].endswith('_'+s)]) for s in ('l', 'r')}
fit_steps = []
for step in range(10):
    f = place_hands(base.copy())
    w = fk(f)
    rp = robe.skin(w)
    bp = body.skin(w)
    torso = rp[torso_ids]
    torso = torso[(torso[:, 2] > 80) & (torso[:, 2] < 121) & (np.abs(torso[:, 0]) < 19)]
    hand_all = np.concatenate([bp[hand_ids[s]] for s in ('l', 'r')])
    tree = cKDTree(torso[:, [0, 2]])
    cells = tree.query_ball_point(hand_all[:, [0, 2]], .85)
    push = max([float(torso[j, 1].max()+1.3-hand_all[i, 1]) for i, j in enumerate(cells) if j] + [0.])
    if push > .01:
        for s in ('l', 'r'):
            targets[s][1] += push
    # The wide cuffs must clear the opposite hand/forearm, including the native
    # 0.28 cm secondary-motion allowance. Same-arm wrist skin is intentional.
    arm_push = {}
    for side, sign, other in (('l', 1, 'r'), ('r', -1, 'l')):
        wrist = w[ix['hand_'+side], :3, 3]
        ids = sleeve_ids[side]
        cuff = rp[ids]
        cuff = cuff[np.linalg.norm(cuff-wrist, axis=1) < 15.]
        obstacle = bp[hand_ids[other]]
        if len(cuff):
            distance, _ = cKDTree(obstacle).query(cuff)
            if np.min(distance) < .65:
                pole_width[side] += 1.3
                arm_push[side] = 1.3
    fit_steps.append({'pair_forward_adjustment_cm': push, 'elbow_outward_adjustment_cm': arm_push})
    if push <= .01 and not arm_push:
        break

base = place_hands(base)
base_world = fk(base)
duration, rate = 12., 30
frames = []
for k in range(round(duration*rate)+1):
    t = k/rate
    cycle = math.tau*t/duration
    # Three calm breaths over 12 seconds, with a small smooth amplitude envelope
    # and slower exhalation harmonic. Every component has a seamless period.
    breath = (math.sin(3*cycle) + .14*math.sin(6*cycle-.35))*(1+.06*math.sin(cycle+.6))
    micro = .14*math.sin(5*cycle+.7)+.06*math.sin(7*cycle+1.4)
    f = base.copy()
    for bone, amount in (('spine_02', .07), ('spine_03', .12), ('spine_04', .23), ('spine_05', .22)):
        rotate_world(f, bone, [1, 0, 0], amount*breath)
    rotate_world(f, 'spine_03', [0, 1, 0], .13*math.sin(cycle))
    rotate_world(f, 'spine_05', [0, 0, 1], .10*math.sin(2*cycle+.3))
    # Submillimetre rib expansion is shared with the skinned robe.
    f[ix['spine_04'], 8:10] *= 1.+.0015*breath
    for side, sign in (('l', 1), ('r', -1)):
        rotate_world(f, 'clavicle_'+side, [0, 1, 0], sign*(.12*breath+.025*micro))
    rotate_world(f, 'neck_01', [1, 0, 0], -.14*breath)
    rotate_world(f, 'head', [1, 0, 0], .07*breath+.045*micro)
    rotate_world(f, 'head', [0, 0, 1], .15*math.sin(cycle+.5))
    # Both hands share one gently moving target. No independent jitter that
    # would break palm contact or produce interpenetrating fingers.
    offset = np.array([.06*math.sin(cycle), .055*breath, .075*breath+.018*micro])
    place_hands(f, offset)
    frames.append(f)
frames[-1] = frames[0].copy()
data = np.asarray(frames)
for frame in range(1, len(data)):
    flip = (data[frame-1, :, 3:7]*data[frame, :, 3:7]).sum(axis=1) < 0
    data[frame, flip, 3:7] *= -1
out = dict(mesh=rig['mesh'], skeleton=rig['skeleton'], names=names, parents=parents,
           reference=rig['reference'], rate=rate, duration=duration, frames=data.tolist(),
           source='Newly authored from user standing reference; native Kaitlin support pose',
           source_idle=rig['source_idle'], root_motion=False,
           hand_targets_cm={s: v.tolist() for s, v in targets.items()},
           hand_rotations={s: v.tolist() for s, v in rotations.items()},
           fit_steps=fit_steps, runtime_tested=False)
(OUT/'authored.json').write_text(json.dumps(out, separators=(',', ':')), encoding='utf-8')
ref_image = Path('C:/Users/allan/AppData/Local/Temp/codex-clipboard-9e6047cf-8869-4ed4-82e5-2ba3d2bb1286.png')
if ref_image.exists():
    shutil.copy2(ref_image, OUT/'standing_reference.png')
print('NUN_IDLE_AUTHORED', len(frames), 'frames', 'targets', out['hand_targets_cm'], 'elbow_widths', pole_width, flush=True)
