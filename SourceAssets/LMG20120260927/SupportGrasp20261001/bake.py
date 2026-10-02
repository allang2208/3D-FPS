"""Bake no-grip-only local corrections; source animation packages stay unchanged."""
import gzip
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from scipy.ndimage import gaussian_filter1d

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT / 'SourceAssets/PKMLowpoly20260922/GripLayer56'))
import evaluate as EV
import author as AH

inp = json.loads((HERE / 'inputs.json').read_text())
target = json.loads((HERE / 'target.json').read_text())
names = json.loads((PROJECT / 'SourceAssets/PKMLowpoly20260922/ArmHinge55/Inputs/201_bind.json').read_text())
parents = {n: names['names'][p] for n, p in zip(names['names'], names['parents']) if p >= 0}
finger_names = list(target['locals'])
arm_names = AH.WRITE
bind = AH.Bind('201')

def load(spec):
    with gzip.open(spec['file'], 'rt', encoding='utf8') as f:
        d = json.load(f)
    return d, {n: np.array([AH.mat(frame[i]) for frame in d['world']]) for i, n in enumerate(d['bones'])}

idle, m0 = load(inp['201']['/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle'])
G0 = np.linalg.inv(m0['WPN_root'][0]) @ m0['hand_l'][0]
G1 = np.array(target['hand_gun'])
offset = np.linalg.inv(G0) @ G1
offset_rotation = Rot.from_matrix(AH.rot(offset)).as_rotvec()
offset_location = offset[:3, 3] * 100.0
target_local = {n: np.array(v) for n, v in target['locals'].items()}
output = {'revision': 'SupportGrasp20261001', 'family': 'base', 'source_animations_changed': False,
          'source_reference': target['reference'], 'clips': {}, 'runtime_tested': False}

for asset, spec in inp['201'].items():
    d, m = load(spec)
    count = len(d['times'])
    times = np.array(d['times'])
    fps = (count - 1) / max(d['seconds'], 1e-6)
    raw_weight = []
    for frame in range(count):
        H = np.linalg.inv(m['WPN_root'][frame]) @ m['hand_l'][frame]
        distance = np.linalg.norm((H[:3, 3] - G0[:3, 3]) * 100.0)
        angle = EV.ang(AH.rot(G0).T @ AH.rot(H))
        raw_weight.append((1.0 - EV.ss((3.5, 5.5), distance)) * (1.0 - EV.ss((32.0, 48.0), angle)))
    raw_weight = np.array(raw_weight)
    # A short, bounded authoring blend follows the source release/return. Clamp
    # to zero at free-hand contacts; preserve exact held endpoints for blending.
    weights = gaussian_filter1d(raw_weight, max(.5, fps * .045), mode='nearest')
    weights[raw_weight <= 1e-6] = 0.0
    weights[0], weights[-1] = raw_weight[0], raw_weight[-1]
    weights = weights * weights * (3.0 - 2.0 * weights)
    tracks = {n: [] for n in arm_names + finger_names}
    previous = {n: None for n in tracks}
    authored_tracks = {n: [] for n in tracks}
    authored_previous = {n: None for n in tracks}
    for frame, weight in enumerate(weights):
        local_original = {n: np.linalg.inv(m[parents[n]][frame]) @ m[n][frame] for n in tracks}
        local_new = {n: L.copy() for n, L in local_original.items()}
        if weight > 1e-6:
            Rw = AH.rot(m['WPN_root'][frame]); Pw = m['WPN_root'][frame][:3, 3]
            R = np.array([AH.rot(m[n][frame]) for n in AH.BONES])
            P = np.array([m[n][frame][:3, 3] for n in AH.BONES])
            Hrot = Rw.T @ R[AH.HA]
            Hp = Rw.T @ (P[AH.HA] - Pw)
            Rt = Rw @ Hrot @ Rot.from_rotvec(weight * offset_rotation).as_matrix()
            Pt = Pw + Rw @ (Hp + Hrot @ (weight * offset_location))
            Rn, Pn, _ = EV.layer_arm(R, P, Rt, Pt, 0.0, P[AH.LO] - P[AH.UP], bind, 0.0)
            world_new = {}
            for i, n in enumerate(AH.BONES):
                W = m[n][frame].copy()
                W[:3, :3] = Rn[i] * np.linalg.norm(W[:3, :3], axis=0)
                W[:3, 3] = Pn[i]
                world_new[n] = W
            for n in arm_names:
                local_new[n] = np.linalg.inv(world_new[parents[n]]) @ world_new[n]
            for n in finger_names:
                R0, R1 = AH.rot(local_original[n]), AH.rot(target_local[n])
                Rn = R0 @ Rot.from_rotvec(weight * Rot.from_matrix(R0.T @ R1).as_rotvec()).as_matrix()
                local_new[n][:3, :3] = Rn * np.linalg.norm(local_original[n][:3, :3], axis=0)
        for n in tracks:
            old, new = local_original[n], local_new[n]
            row, authored_previous[n] = AH.pack(new, authored_previous[n])
            authored_tracks[n].append(row)
            q = Rot.from_matrix(AH.rot(new) @ AH.rot(old).T).as_quat()
            if previous[n] is not None and q @ previous[n] < 0:
                q = -q
            previous[n] = q
            tracks[n].append([*(new[:3, 3] - old[:3, 3]), *q, 0.0, 0.0, 0.0])
    sparse = {}
    for bone, rows in tracks.items():
        rows = np.array(rows)
        if np.max(np.abs(rows[:, :3])) < 1e-10 and np.max(np.abs(rows[:, 3:6])) < 1e-10:
            continue
        constant = np.max(np.abs(rows - rows[0])) < 1e-7
        sparse[bone] = {'times': [float(times[0])] if constant else times.tolist(),
                        'values': rows[:1].reshape(-1).tolist() if constant else rows.reshape(-1).tolist()}
    output['clips'][asset] = {'duration': d['seconds'], 'source_sha256': spec['sha256'], 'tracks': sparse,
                            'authored_tracks': {n: authored_tracks[n] for n in sparse}}
    print('SUPPORTGRASP_BAKED', asset, len(sparse), flush=True)
with gzip.open(HERE / 'profile.json.gz', 'wt', encoding='utf8') as f:
    json.dump(output, f, separators=(',', ':'))
print('SUPPORTGRASP_DATA_COMPLETE', len(output['clips']), flush=True)
