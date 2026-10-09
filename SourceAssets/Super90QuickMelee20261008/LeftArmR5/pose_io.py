"""Native Super90 source-key and grip-delta conversion (metres in author space)."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

O = Path(__file__).parent
OLD = O  # Self-contained retained authoring inputs; earlier revisions are archived.
A = json.loads((OLD / 'author_space.json').read_text())
U = json.loads((OLD / 'inputs.json').read_text())
D = json.loads((O / 'installed_source.json').read_text())
names, parents = A['names'], A['parents']
rest = {n: np.array(m) for n, m in A['rest'].items()}
times = np.arange(D['frames'] + 1) / D['fps']
C, E = np.array(A['conversion']['C']), np.array(A['conversion']['E'])
Ci, Ei = np.linalg.inv(C), np.linalg.inv(E)
K = {n: np.array(m) for n, m in A['conversion']['K'].items()}
Ki = {n: np.linalg.inv(m) for n, m in K.items()}
WRITE = ['upperarm_l', 'lowerarm_l', 'lowerarm_aux_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']

def unit(v):
    return v / max(np.linalg.norm(v), 1e-12)

def rot(m):
    return R.from_matrix(m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0))

def mat(v):
    m = np.eye(4)
    m[:3, :3] = R.from_quat(v[3:7]).as_matrix() * v[7:10]
    m[:3, 3] = v[:3]
    return m

def pack(m):
    return np.r_[m[:3, 3], rot(m).as_quat(), np.linalg.norm(m[:3, :3], axis=0)]

def values(t):
    v = np.array(t['values']).reshape(-1, 10)
    if len(v) == 1:
        return np.tile(v, (len(times), 1))
    ts = np.array(t['times'])
    out = np.array([np.interp(times, ts, v[:, i]) for i in range(10)]).T
    out[:, 3:7] = Slerp(ts, R.from_quat(v[:, 3:7]))(np.clip(times, ts[0], ts[-1])).as_quat()
    return out

def decode(family):
    local = {t['bone']: values(t) for t in D['base_tracks']}
    if family != 'base':
        for track in D['profiles'][family]['clip']['tracks']:
            n = track['bone']; delta = values(track)
            local[n][:, :3] += delta[:, :3]
            local[n][:, 3:7] = (R.from_quat(delta[:, 3:7]) * R.from_quat(local[n][:, 3:7])).as_quat()
            local[n][:, 7:] += delta[:, 7:]
    poses = []
    for i in range(len(times)):
        world = {}
        for n in U['names']:
            world[n] = world.get(U['parents'][n], np.eye(4)) @ mat(local[n][i])
        poses.append({n: E @ Ci @ world[n] @ Ki[n] for n in names})
    return poses, local

def encode(pose):
    world = {n: C @ Ei @ m @ K[n] for n, m in pose.items()}
    return {n: pack(np.linalg.inv(world[parents[n]]) @ world[n]) for n in WRITE}

def track(n, v):
    v = np.array(v).copy()
    for i in range(1, len(v)):
        if v[i - 1, 3:7] @ v[i, 3:7] < 0:
            v[i, 3:7] *= -1
    constant = np.max(np.abs(v - v[0])) < 1e-7
    return dict(bone=n, times=[0.] if constant else times.tolist(),
                values=v[0].tolist() if constant else v.ravel().tolist())
