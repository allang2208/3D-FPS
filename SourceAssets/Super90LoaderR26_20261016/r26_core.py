"""Shared helpers: installed local rows -> component space, grip overlays and arm re-solve."""
import json, math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
NAMES, PARENTS = D['names'], D['parents']
FAMILIES = tuple(D['profiles'])
FPS = 60
I4 = np.eye(4)
POST, TUBE, GUN = 'WPN_SOCKET_Magazine', 'WPN_Shell', 'WPN_root'
ARM = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'lowerarm_aux_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
DIGITS = ('index', 'middle', 'ring', 'pinky', 'thumb')
FINGERS = [n for n in NAMES if n.endswith('_l') and n.split('_')[0] in DIGITS]


def matrix(v):
    m = I4.copy()
    m[:3, :3] = R.from_quat(v[3:7]).as_matrix() * np.asarray(v[7:])
    m[:3, 3] = v[:3]
    return m


def pack(m):
    s = np.linalg.norm(m[:3, :3], axis=0)
    return np.r_[m[:3, 3], R.from_matrix(m[:3, :3] / s).as_quat(), s]


def world(row):
    out = {}
    for n in NAMES:
        out[n] = out.get(PARENTS[n], I4) @ matrix(row[n])
    return out


def local_rows(world_rows):
    out = []
    for w in world_rows:
        out.append({n: pack(np.linalg.inv(w[PARENTS[n]]) @ w[n]) if PARENTS[n] in w else pack(w[n]) for n in NAMES})
    return out


def overlay_samples(track, times):
    ts = np.array(track['times'])
    v = np.array(track['values']).reshape(-1, 10)
    if len(ts) == 1:
        return np.repeat(v, len(times), axis=0)
    times = np.clip(times, ts[0], ts[-1])
    delta = np.array([np.interp(times, ts, v[:, i]) for i in range(10)]).T
    delta[:, 3:7] = Slerp(ts, R.from_quat(v[:, 3:7]))(times).as_quat()
    return delta


def posed_local(role, family='base'):
    """Local rows exactly as FSuper90GripLayer applies a family delta (additive t/s, pre-multiplied q)."""
    clip = D['clips'][role]
    rows = [{n: np.array(v, float) for n, v in row.items()} for row in clip['rows']]
    if family == 'base':
        return rows
    for track in D['profiles'][family]['clips'][clip['path']]['tracks']:
        n = track['bone']
        for row, d in zip(rows, overlay_samples(track, clip['times'])):
            row[n][:3] += d[:3]
            row[n][3:7] = (R.from_quat(d[3:7]) * R.from_quat(row[n][3:7])).as_quat()
            row[n][7:] += d[7:]
    return rows


def norm(v):
    return v / max(np.linalg.norm(v), 1e-12)


def basis(axis, normal):
    x = norm(axis)
    z = norm(normal - x * np.dot(normal, x))
    return np.column_stack([x, np.cross(z, x), z])


def between(a, b):
    a, b = norm(a), norm(b)
    axis = np.cross(a, b)
    length = np.linalg.norm(axis)
    return np.eye(3) if length < 1e-10 else R.from_rotvec(axis / length * math.atan2(length, np.dot(a, b))).as_matrix()


REST = {n: matrix(v) for n, v in json.loads((O.parent / 'Super90Foregrips20261007/native.json').read_text())['rest'].items()}
_fore = REST['hand_l'][:3, 3] - REST['lowerarm_l'][:3, 3]
STATIONS = {n: float(np.clip(np.dot(REST[n][:3, 3] - REST['lowerarm_l'][:3, 3], _fore) / np.dot(_fore, _fore), 0, 1))
            for n in ARM if n.startswith('lowerarm_') and n != 'lowerarm_l'}


def solve_arm(w, hand, pole=None):
    """Move the left wrist to `hand` with the shoulder fixed and both segment lengths kept.

    Same construction as Super90LoaderArmRoot support_pose: bend plane carried from
    the installed elbow (or `pole` = (axis, elbow direction) of a retimed source
    frame), forearm helpers keep their stations along the forearm and share the
    hand's added axial twist by station."""
    a, e0, t0 = (w[n][:3, 3] for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
    t = hand[:3, 3]
    l1, l2 = np.linalg.norm(e0 - a), np.linalg.norm(t0 - e0)
    d = np.linalg.norm(t - a)
    if d >= .999 * (l1 + l2) or d <= abs(l1 - l2) + 1e-3:
        raise ValueError('Unreachable wrist target')
    axis = norm(t - a)
    if pole is None:
        axis0 = norm(t0 - a)
        pole0 = e0 - a - axis0 * np.dot(e0 - a, axis0)
    else:
        axis0, pole0 = pole
    pole = norm(between(axis0, axis) @ pole0)
    s = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    e = a + axis * s + pole * math.sqrt(max(0., l1 * l1 - s * s))
    normal0, normal = np.cross(e0 - a, t0 - e0), np.cross(e - a, t - e)
    qu = basis(e - a, normal) @ basis(e0 - a, normal0).T
    qf = basis(t - e, normal) @ basis(t0 - e0, normal0).T
    mu, mf = I4.copy(), I4.copy()
    mu[:3, :3], mu[:3, 3] = qu, a - qu @ a
    mf[:3, :3], mf[:3, 3] = qf, e - qf @ e0
    out = dict(w)
    out['upperarm_l'] = mu @ w['upperarm_l']
    out['lowerarm_l'] = mf @ w['lowerarm_l']
    fa = norm(t - e)
    dq = R.from_matrix(hand[:3, :3]) * (R.from_matrix(qf) * R.from_matrix(w['hand_l'][:3, :3])).inv()
    q = dq.as_quat()
    twist = 2 * math.atan2(np.dot(q[:3], fa), q[3])
    twist = (twist + math.pi) % (2 * math.pi) - math.pi
    for n, station in STATIONS.items():
        m = mf @ w[n]
        centre = e + (t - e) * station
        turn = R.from_rotvec(fa * twist * station).as_matrix()
        m[:3, 3] = centre + turn @ (m[:3, 3] - centre)
        m[:3, :3] = turn @ m[:3, :3]
        out[n] = m
    out['hand_l'] = hand
    # Fingers and every other descendant keep their installed local transforms.
    for n in NAMES:
        if n not in ARM and PARENTS[n] in out and _descends(n, 'hand_l'):
            out[n] = out[PARENTS[n]] @ (np.linalg.inv(w[PARENTS[n]]) @ w[n])
    return out


_desc = {}
def _descends(n, root):
    key = (n, root)
    if key not in _desc:
        p, found = PARENTS.get(n), False
        while p:
            if p == root:
                found = True
                break
            p = PARENTS.get(p)
        _desc[key] = found
    return _desc[key]
