"""Use the accepted idle right chain in gun space for walk/run only."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
names, parents = D['names'], D['parents']


def under(n, root):
    while n in parents:
        if n == root:
            return True
        n = parents[n]
    return False


RIGHT = [n for n in names if under(n, 'clavicle_r')]


def matrix(v):
    m = np.eye(4)
    m[:3, :3] = R.from_quat(v[3:7]).as_matrix() * v[7:]
    m[:3, 3] = v[:3]
    return m


def pack(m):
    scale = np.linalg.norm(m[:3, :3], axis=0)
    return np.r_[m[:3, 3], R.from_matrix(m[:3, :3] / scale).as_quat(), scale]


def world(row):
    out = {}
    for n in names:
        out[n] = out.get(parents[n], np.eye(4)) @ matrix(row[n])
    return out


def sample_delta(t, time):
    ts = np.array(t['times'])
    values = np.array(t['values']).reshape(-1, 10)
    if len(ts) == 1:
        return values[0]
    at = np.clip(time, ts[0], ts[-1])
    v = np.array([np.interp(at, ts, values[:, i]) for i in range(10)])
    v[3:7] = Slerp(ts, R.from_quat(values[:, 3:7]))([at]).as_quat()[0]
    return v


def apply_profile(row, clip, time):
    out = {n: np.array(v, dtype=float) for n, v in row.items()}
    for t in clip['tracks']:
        v, delta = out[t['bone']], sample_delta(t, time)
        v[:3] += delta[:3]
        v[3:7] = (R.from_quat(delta[3:7]) * R.from_quat(v[3:7])).as_quat()
        v[7:] += delta[7:]
    return out


def rehold(row, reference):
    posed = world(row)
    gun_motion = posed['WPN_root'] @ np.linalg.inv(reference['WPN_root'])
    # Transport the complete accepted chain, including aux/twist and digits.
    # No independent wrist offset, altered segment lengths or new IK posture.
    for n in RIGHT:
        posed[n] = gun_motion @ reference[n]
    out = {n: np.array(v) for n, v in row.items()}
    for n in RIGHT:
        out[n] = pack(np.linalg.inv(posed[parents[n]]) @ posed[n])
    return out


def track(n, values, times):
    v = np.array(values)
    for i in range(1, len(v)):
        if v[i - 1, 3:7] @ v[i, 3:7] < 0:
            v[i, 3:7] *= -1
    constant = np.max(np.abs(v - v[0])) < 1e-7
    return dict(bone=n, times=[0.] if constant else times,
                values=v[0].tolist() if constant else v.ravel().tolist())


idle = D['clips']['idle']
base_reference = world(idle['rows'][0])
patch = dict(revision='Super90LocomotionIdleGrip-20261010', right_bones=RIGHT,
             idle_reference=idle['path'], clips={}, profiles={}, runtime_tested=False)
base_rows = {}
for role in ('walk', 'run'):
    c = D['clips'][role]
    rows = [rehold(row, base_reference) for row in c['rows']]
    base_rows[role] = rows
    patch['clips'][role] = dict(path=c['path'], duration=c['duration'], frames=c['frames'], times=c['times'],
        tracks=[track(n, [r[n] for r in rows], c['times']) for n in RIGHT])
for family, spec in D['profiles'].items():
    idle_layer = spec['clips'][idle['path']]
    reference = world(apply_profile(idle['rows'][0], idle_layer, 0.))
    result = dict(path=spec['path'], clips={})
    for role in ('walk', 'run'):
        c = D['clips'][role]
        layer = spec['clips'][c['path']]
        rows = [rehold(apply_profile(row, layer, t), reference) for row, t in zip(c['rows'], c['times'])]
        tracks = []
        for n in RIGHT:
            delta = []
            for b, p in zip(base_rows[role], rows):
                bv, pv = b[n], p[n]
                q = (R.from_quat(pv[3:7]) * R.from_quat(bv[3:7]).inv()).as_quat()
                if q[3] < 0:
                    q *= -1
                delta.append(np.r_[pv[:3] - bv[:3], q, pv[7:] - bv[7:]])
            if np.max(np.abs(np.array(delta) - np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0]))) > 1e-7:
                tracks.append(track(n, delta, c['times']))
        result['clips'][c['path']] = dict(base=c['path'], duration=c['duration'], tracks=tracks)
    patch['profiles'][family] = result
(O / 'animation_patch.json').write_text(json.dumps(patch, separators=(',', ':')))
print('SUPER90_LOCOMOTION_IDLE_GRIP_AUTHORED', len(RIGHT), 'right bones; walk/run and four profiles', flush=True)
