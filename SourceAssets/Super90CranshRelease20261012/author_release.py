"""Restore Cransh's authored release tail without replacing the accepted feeds or rig."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
SOURCE = json.loads((O.parent / 'Super90NativeEmptyBolt20261010/inputs.json').read_text())
NAMES, PARENTS = D['names'], D['parents']
FPS, TAIL, END = 60, 360, 424
TIMES = (np.arange(END + 1) / FPS).tolist()


def matrix(v):
    m = np.eye(4)
    m[:3, :3] = R.from_quat(v[3:7]).as_matrix() * v[7:]
    m[:3, 3] = v[:3]
    return m


def pack(m):
    scale = np.linalg.norm(m[:3, :3], axis=0)
    return np.r_[m[:3, 3], R.from_matrix(m[:3, :3] / scale).as_quat(), scale]


def sample(t, time):
    ts, v = np.array(t['times']), np.array(t['values']).reshape(-1, 10)
    if len(v) == 1:
        return v[0].copy()
    time = float(np.clip(time, ts[0], ts[-1]))
    out = np.array([np.interp(time, ts, v[:, i]) for i in range(10)])
    out[3:7] = Slerp(ts, R.from_quat(v[:, 3:7]))([time]).as_quat()[0]
    return out


def world(row):
    out = {}
    for n in NAMES:
        out[n] = out.get(PARENTS[n], np.eye(4)) @ matrix(row[n])
    return out


def posed(data, family, role='empty'):
    clip = data['clips'][role]
    rows = [{n: np.array(v) for n, v in row.items()} for row in clip['rows']]
    if family != 'base':
        layer = data['profiles'][family]['clips'][clip['path']]
        for row, time in zip(rows, clip['times']):
            for t in layer['tracks']:
                v, delta = row[t['bone']], sample(t, time)
                v[:3] += delta[:3]
                v[3:7] = (R.from_quat(delta[3:7]) * R.from_quat(v[3:7])).as_quat()
                v[7:] += delta[7:]
    return rows


def arc_rotation(a, b):
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    cross = np.cross(a, b)
    length = np.linalg.norm(cross)
    if length < 1.e-10:
        return np.eye(3)
    return R.from_rotvec(cross / length * np.arctan2(length, np.dot(a, b))).as_matrix()


def carry_hand(old, target):
    """Move the existing elbow plane to the accepted grip with native bone lengths."""
    p = {n: m.copy() for n, m in old.items()}
    s, e, w = [old[n][:3, 3].copy() for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
    goal = target[:3, 3]
    upper, lower = np.linalg.norm(e - s), np.linalg.norm(w - e)
    axis = goal - s
    length = np.linalg.norm(axis)
    axis /= length
    if length > (upper + lower) * .985:
        shift = axis * (length - (upper + lower) * .985)
        s += shift
        p['clavicle_l'][:3, 3] += shift
        length = (upper + lower) * .985
    length = max(abs(upper - lower) + 1.e-8, length)
    along = (upper * upper - lower * lower + length * length) / (2 * length)
    pole = e - old['upperarm_l'][:3, 3]
    pole -= axis * np.dot(pole, axis)
    pole /= np.linalg.norm(pole)
    elbow = s + axis * along + pole * np.sqrt(max(0., upper * upper - along * along))
    p['upperarm_l'][:3, :3] = arc_rotation(e - old['upperarm_l'][:3, 3], elbow - s) @ old['upperarm_l'][:3, :3]
    p['upperarm_l'][:3, 3] = s
    p['lowerarm_l'][:3, :3] = arc_rotation(w - e, goal - elbow) @ old['lowerarm_l'][:3, :3]
    p['lowerarm_l'][:3, 3] = elbow
    fore = p['lowerarm_l'] @ np.linalg.inv(old['lowerarm_l'])
    for n in ('lowerarm_aux_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l'):
        p[n] = fore @ old[n]
    p['hand_l'] = target
    return p


def smooth(x):
    x = float(np.clip(x, 0., 1.))
    return x*x*(3.-2.*x)


def blend(a, b, weight):
    out = a*(1.-weight)+b*weight
    out[3:7] = Slerp([0., 1.], R.from_quat([a[3:7], b[3:7]]))([weight]).as_quat()[0]
    return out


def track(n, values):
    values = np.array(values)
    for i in range(1, len(values)):
        if values[i-1, 3:7] @ values[i, 3:7] < 0:
            values[i, 3:7] *= -1
    constant = np.max(np.abs(values - values[0])) < 1.e-8
    return dict(bone=n, times=[0.] if constant else TIMES,
                values=values[0].tolist() if constant else values.ravel().tolist())


current, original = posed(D, 'base'), posed(SOURCE, 'base')
# The original 360 boundary is already the same pose as the installed feed.
base = current[:TAIL + 1] + original[TAIL + 1:END + 1]
bolt = np.array([world(row)['WPN_bolt'][:3, 3] for row in base])
# Mechanical timing is measured in the bolt's parent space, excluding gun motion.
bolt_local = np.array([row['WPN_bolt'][:3] for row in original])
travel = np.linalg.norm(bolt_local[TAIL] - bolt_local[-1])
remaining = np.linalg.norm(bolt_local - bolt_local[-1], axis=1) / travel
release_frame = next(f for f in range(TAIL, END + 1) if remaining[f] < .99)
closed_frame = next(f for f in range(TAIL, END + 1) if remaining[f] < .01)
out = dict(revision='Super90-Cransh-BoltRelease-20261012', path=D['clips']['empty']['path'],
           previous_duration=D['clips']['empty']['duration'], frames=END, fps=FPS,
           duration=END/FPS, tail_begin=TAIL/FPS, release_frame=release_frame,
           closed_frame=closed_frame, bolt_release_sound=closed_frame/FPS,
           bolt_ready=closed_frame/FPS,
           reference_url='https://sketchfab.com/3d-models/fps-benelli-m4-animations-225a62190f6043ca975eaa2798ab7e2c',
           tracks=[track(n, [row[n] for row in base]) for n in NAMES], profiles={}, runtime_tested=False)
digits = [n for n in NAMES if n.endswith('_l') and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))]
chain = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'lowerarm_aux_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
for family, spec in D['profiles'].items():
    installed, donor = posed(D, family), posed(SOURCE, family)
    old_anchor, new_anchor = world(donor[TAIL]), world(installed[TAIL])
    old_grip = np.linalg.inv(old_anchor['WPN_root']) @ old_anchor['hand_l']
    new_grip = np.linalg.inv(new_anchor['WPN_root']) @ new_anchor['hand_l']
    offset = np.linalg.inv(old_grip) @ new_grip
    rows = installed[:TAIL + 1]
    # Preserve the current grouped fingers while the support hand stays on its grip.
    # There is no proximity-driven fade during the release gesture.
    for frame in range(TAIL + 1, END + 1):
        row = {n: v.copy() for n, v in donor[frame].items()}
        old = world(row)
        carried = carry_hand(old, old['hand_l'] @ offset)
        local = {n: pack(np.linalg.inv(carried.get(PARENTS[n], np.eye(4))) @ carried[n]) for n in chain}
        for n in chain:
            # Retain native segment translations/scales; only the clavicle may shift.
            if n != 'clavicle_l':
                local[n][:3] = row[n][:3]
            local[n][7:] = row[n][7:]
            row[n] = local[n]
        for n in digits:
            row[n] = installed[TAIL][n].copy()
        # The carried arm meets the preserved last-feed pose without a one-frame jump.
        weight = smooth((frame - TAIL) / 10.)
        for n in chain:
            correction = (R.from_quat(installed[TAIL][n][3:7]) * R.from_quat(donor[TAIL][n][3:7]).inv())
            continued = donor[frame][n].copy()
            continued[3:7] = (correction * R.from_quat(continued[3:7])).as_quat()
            continued[:3] += installed[TAIL][n][:3] - donor[TAIL][n][:3]
            row[n] = blend(continued, row[n], weight)
        rows.append(row)
    deltas = []
    for n in NAMES:
        values = []
        for a, b in zip(base, rows):
            q = (R.from_quat(b[n][3:7]) * R.from_quat(a[n][3:7]).inv()).as_quat()
            if q[3] < 0:
                q *= -1
            values.append(np.r_[b[n][:3]-a[n][:3], q, b[n][7:]-a[n][7:]])
        if np.max(np.abs(np.array(values)-np.array([0,0,0,0,0,0,1,0,0,0]))) > 1.e-7:
            deltas.append(track(n, values))
    out['profiles'][family] = dict(path=spec['path'], clip=dict(base=out['path'], duration=out['duration'], tracks=deltas))
(O / 'animation_patch.json').write_text(json.dumps(out, separators=(',', ':')))
(O / 'timing.json').write_text(json.dumps({k:v for k,v in out.items() if k not in ('tracks','profiles')}, indent=2))
print('CRANSH_RELEASE_AUTHORED', {'frames': END, 'release': release_frame, 'closed': closed_frame,
      'feed_frames_preserved': TAIL, 'families': list(out['profiles'])}, flush=True)
