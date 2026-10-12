"""Join the installed loader withdrawal to the installed Cransh button release.

Both inputs use the unchanged Super90 native rig. Arm roots interpolate in gun
space so the rear hand retains its grip until the support hand has returned.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
NAMES, PARENTS = D['names'], D['parents']
FPS, WITHDRAW, SUPPORT, PRESS, CYCLE_PRESS = 60, 125, 144, 160, 16
DONOR_BEGIN, DONOR_END, DONOR_CLOSED = 360, 424, 374


def matrix(v):
    m = np.eye(4)
    m[:3, :3] = R.from_quat(v[3:7]).as_matrix() * v[7:]
    m[:3, 3] = v[:3]
    return m


def pack(m):
    s = np.linalg.norm(m[:3, :3], axis=0)
    return np.r_[m[:3, 3], R.from_matrix(m[:3, :3] / s).as_quat(), s]


def world(row):
    out = {}
    for n in NAMES:
        out[n] = out.get(PARENTS[n], np.eye(4)) @ matrix(row[n])
    return out


def smooth(x):
    x = float(np.clip(x, 0., 1.))
    return x*x*(3.-2.*x)


def blend(a, b, weight):
    out = a*(1.-weight) + b*weight
    out[3:7] = Slerp([0., 1.], R.from_quat([a[3:7], b[3:7]]))([weight]).as_quat()[0]
    return out


def posed(role, family):
    clip = D['clips'][role]
    rows = [{n: np.array(v) for n, v in row.items()} for row in clip['rows']]
    if family == 'base':
        return rows
    layer = D['profiles'][family]['clips'][clip['path']]
    for track in layer['tracks']:
        ts = np.array(track['times'])
        v = np.array(track['values']).reshape(-1, 10)
        times = np.clip(clip['times'], ts[0], ts[-1])
        if len(ts) == 1:
            delta = np.repeat(v, len(rows), axis=0)
        else:
            delta = np.array([np.interp(times, ts, v[:, i]) for i in range(10)]).T
            delta[:, 3:7] = Slerp(ts, R.from_quat(v[:, 3:7]))(times).as_quat()
        n = track['bone']
        for row, d in zip(rows, delta):
            row[n][:3] += d[:3]
            row[n][3:7] = (R.from_quat(d[3:7]) * R.from_quat(row[n][3:7])).as_quat()
            row[n][7:] += d[7:]
    return rows


def author(role, family):
    original, donor = posed(role, family), posed('release', family)
    cycle = role == 'cycle'
    start, support, press = (0, 0, CYCLE_PRESS) if cycle else (WITHDRAW, SUPPORT, PRESS)
    a, b = original[start], donor[0]
    wa, wb = world(a), world(b)
    anchors = {}
    for side in ('l', 'r'):
        n = 'clavicle_' + side
        anchors[side] = (pack(np.linalg.inv(wa['WPN_root']) @ wa[n]),
                         pack(np.linalg.inv(wb['WPN_root']) @ wb[n]))
    rows = original[:start + 1]
    for frame in range(start + 1, press):
        overall = smooth((frame-start)/(press-start))
        weights = {'l': overall if cycle else smooth((frame-start)/(support-start)),
                   'r': smooth((frame-support)/(press-support))}
        row = {n: blend(a[n], b[n], weights[n[-1]] if n.endswith(('_l', '_r')) else overall)
               for n in NAMES}
        w = world(row)
        for side in ('l', 'r'):
            n = 'clavicle_' + side
            relative = matrix(blend(*anchors[side], weights[side]))
            row[n] = pack(np.linalg.inv(w[PARENTS[n]]) @ w['WPN_root'] @ relative)
        rows.append(row)
    # Includes the actual button contact, bolt closure and authored hand recovery.
    rows.extend(donor)
    return rows


def track(n, values):
    values = np.array(values)
    for i in range(1, len(values)):
        if values[i-1, 3:7] @ values[i, 3:7] < 0:
            values[i, 3:7] *= -1
    constant = np.max(np.abs(values-values[0])) < 1.e-8
    return dict(bone=n, times=[0.] if constant else (np.arange(len(values))/FPS).tolist(),
                values=values[0].tolist() if constant else values.ravel().tolist())


out = dict(revision='Super90-Loader-ButtonRelease-20261012', fps=FPS, clips={},
           profiles={f: dict(path=p['path'], clips={}) for f, p in D['profiles'].items()},
           donor=D['clips']['release']['path'], runtime_tested=False)
identity = np.array([0,0,0,0,0,0,1,0,0,0])
for role, source in D['clips'].items():
    if role == 'release':
        continue
    base = author(role, 'base')
    press = CYCLE_PRESS if role == 'cycle' else PRESS
    spec = dict(path=source['path'], source_sha256=source['sha256'],
                previous_duration=source['duration'], frames=len(base)-1, duration=(len(base)-1)/FPS,
                preserved_through=0 if role == 'cycle' else WITHDRAW,
                press_frame=press, closed_frame=press+DONOR_CLOSED-DONOR_BEGIN,
                tracks=[track(n, [row[n] for row in base]) for n in NAMES])
    out['clips'][role] = spec
    for family in D['profiles']:
        rows = author(role, family)
        deltas = []
        for n in NAMES:
            a, b = np.array([r[n] for r in base]), np.array([r[n] for r in rows])
            q = (R.from_quat(b[:, 3:7]) * R.from_quat(a[:, 3:7]).inv()).as_quat()
            q[q[:, 3] < 0] *= -1
            values = np.c_[b[:, :3]-a[:, :3], q, b[:, 7:]-a[:, 7:]]
            if np.max(np.abs(values-identity)) > 1.e-7:
                deltas.append(track(n, values))
        out['profiles'][family]['clips'][spec['path']] = dict(base=spec['path'], duration=spec['duration'], tracks=deltas)
    print('LOADER_BUTTON_AUTHORED', role, spec['frames'], spec['closed_frame'], flush=True)
(O / 'animation_patch.json').write_text(json.dumps(out, separators=(',', ':')))
(O / 'timing.json').write_text(json.dumps(dict(
    fps=FPS, withdrawal_frame=WITHDRAW, support_frame=SUPPORT, press_frame=PRESS,
    closed_frame=PRESS+DONOR_CLOSED-DONOR_BEGIN, end_frame=PRESS+DONOR_END-DONOR_BEGIN,
    cycle_press_frame=CYCLE_PRESS, cycle_closed_frame=CYCLE_PRESS+DONOR_CLOSED-DONOR_BEGIN,
    cycle_end_frame=CYCLE_PRESS+DONOR_END-DONOR_BEGIN,
    runtime_push_extra_frames=6, runtime_push_mapping='Super90LoaderPushTiming.h unchanged',
    donor=out['donor'], runtime_tested=False), indent=2))
