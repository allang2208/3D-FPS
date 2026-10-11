"""Append the installed R24 grasped bolt action to ordinary empty shell feed."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
NAMES, PARENTS = D['names'], D['parents']
FPS, TAIL, BRIDGE, CYCLE_FRAMES = 60, 360, 18, 66
END = TAIL + BRIDGE + CYCLE_FRAMES
TIMES = (np.arange(END + 1) / FPS).tolist()


def ease(x):
    x = np.clip(x, 0., 1.)
    return x * x * x * (10 + x * (-15 + 6 * x))


def matrix(v):
    m = np.eye(4)
    m[:3, :3] = R.from_quat(v[3:7]).as_matrix() * v[7:]
    m[:3, 3] = v[:3]
    return m


def pack(m):
    scale = np.linalg.norm(m[:3, :3], axis=0)
    return np.r_[m[:3, 3], R.from_matrix(m[:3, :3] / scale).as_quat(), scale]


def mix(a, b, w):
    out = np.array(a) * (1 - w) + np.array(b) * w
    out[3:7] = Slerp([0, 1], R.from_quat([a[3:7], b[3:7]]))([float(w)]).as_quat()[0]
    return out


def world(row):
    out = {}
    for n in NAMES:
        out[n] = out.get(PARENTS[n], np.eye(4)) @ matrix(row[n])
    return out


def local(posed):
    return {n: pack(np.linalg.inv(posed.get(PARENTS[n], np.eye(4))) @ posed[n]) for n in NAMES}


def sample(t, time):
    ts = np.array(t['times'])
    v = np.array(t['values']).reshape(-1, 10)
    if len(v) == 1:
        return v[0]
    time = np.clip(time, ts[0], ts[-1])
    out = np.array([np.interp(time, ts, v[:, i]) for i in range(10)])
    out[3:7] = Slerp(ts, R.from_quat(v[:, 3:7]))([time]).as_quat()[0]
    return out


def source(role, family):
    c = D['clips'][role]
    rows = [{n: np.array(v) for n, v in row.items()} for row in c['rows']]
    if family == 'base':
        return rows
    layer = D['profiles'][family]['clips'][c['path']]
    for row, time in zip(rows, c['times']):
        for t in layer['tracks']:
            v, d = row[t['bone']], sample(t, time)
            v[:3] += d[:3]
            v[3:7] = (R.from_quat(d[3:7]) * R.from_quat(v[3:7])).as_quat()
            v[7:] += d[7:]
    return rows


def compose(family):
    feed, cycle = source('empty', family), source('cycle', family)
    a, b = world(feed[TAIL]), world(cycle[0])
    align = a['WPN_root'] @ np.linalg.inv(b['WPN_root'])
    aligned = local({n: align @ b[n] for n in NAMES})
    rows = [{n: v.copy() for n, v in row.items()} for row in feed[:TAIL + 1]]
    open_bolt = feed[TAIL]['WPN_bolt'].copy()
    # Return the feeding right hand first, while retaining the opened bolt.
    # Local-chain interpolation preserves native FK segment lengths; digits
    # fold onto the installed grip instead of independently moving fingertips.
    for f in range(1, BRIDGE + 1):
        row = {n: mix(feed[TAIL][n], aligned[n], ease(f / BRIDGE)) for n in NAMES}
        row['WPN_bolt'] = open_bolt.copy()
        rows.append(row)
    for f in range(1, CYCLE_FRAMES + 1):
        p = world(cycle[f])
        # Carry the entire gun/arms together out of the feed presentation.
        # Alignment has faded before actual handle contact, so the accepted
        # R24 grasp, 5 mm extra pull and release trajectory remain intact.
        offset = matrix(mix(pack(align), pack(np.eye(4)), ease(f / 20)))
        row = local({n: offset @ p[n] for n in NAMES})
        # The donor begins at closed idle. Ordinary empty feed already holds
        # the bolt open; do not close/reopen it while the left hand approaches.
        if f <= 18:
            row['WPN_bolt'] = open_bolt.copy()
        rows.append(row)
    return rows


def track(n, values):
    v = np.array(values)
    for i in range(1, len(v)):
        if v[i - 1, 3:7] @ v[i, 3:7] < 0:
            v[i, 3:7] *= -1
    constant = np.max(np.abs(v - v[0])) < 1e-7
    return dict(bone=n, times=[0.] if constant else TIMES,
                values=v[0].tolist() if constant else v.ravel().tolist())


base = compose('base')
out = dict(revision='Super90NativeEmpty-GraspedBolt-20261010', path=D['clips']['empty']['path'],
    previous_duration=D['clips']['empty']['duration'], frames=END, fps=FPS, duration=END / FPS,
    tail_begin=TAIL / FPS, cycle_begin=(TAIL + BRIDGE) / FPS,
    bolt_pull=(TAIL + BRIDGE + 32.218914) / FPS,
    bolt_release_sound=(TAIL + BRIDGE + 38.382387) / FPS,
    bolt_ready=(TAIL + BRIDGE) / FPS + 1.1 * 32 / 52,
    tracks=[track(n, [row[n] for row in base]) for n in NAMES], profiles={}, runtime_tested=False)
for family, spec in D['profiles'].items():
    rows = compose(family)
    tracks = []
    for n in NAMES:
        delta = []
        for a, b in zip(base, rows):
            q = (R.from_quat(b[n][3:7]) * R.from_quat(a[n][3:7]).inv()).as_quat()
            if q[3] < 0:
                q *= -1
            delta.append(np.r_[b[n][:3] - a[n][:3], q, b[n][7:] - a[n][7:]])
        if np.max(np.abs(np.array(delta) - np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0]))) > 1e-7:
            tracks.append(track(n, delta))
    out['profiles'][family] = dict(path=spec['path'], clip=dict(base=out['path'], duration=out['duration'], tracks=tracks))
(O / 'animation_patch.json').write_text(json.dumps(out, separators=(',', ':')))
(O / 'timing.json').write_text(json.dumps({k: v for k, v in out.items() if k not in ('tracks', 'profiles')}, indent=2))
print('SUPER90_NATIVE_EMPTY_AUTHORED', out['duration'], 'seconds; preserved feed, 0.3s right return, 1.1s installed bolt action', flush=True)
