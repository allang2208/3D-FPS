"""Accepted V9 bare-arm surface on SK_M4_BareArmsV7, the arm mesh the off-hand layer renders.

The rollout's per-mesh Work payloads were archived. BareArmsV7 vertices coincide with the M4 viewmodel's
pre-V9 positions (max 0 cm), so the V9 positions, per-corner UVs, weight overrides and JC_ shapes of
SourceAssets/BareSkinV9M4_20261017/Work/install_payload.json transfer by position. Pose4 JC_Pose_* examples
are not part of that payload and are absent from previews built on this surface.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT/'SourceAssets/BareSkinV9Rollout_20261017/Snapshots/01e184ddd1b7.json'
PAYLOAD = ROOT/'SourceAssets/BareSkinV9M4_20261017/Work/install_payload.json'
M4_SNAPSHOT = ROOT/'SourceAssets/BareHandAudit20261016/Final/56a5bcfd1c23.json'


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def load():
    snap, pay, m4 = read(SNAPSHOT), read(PAYLOAD), read(M4_SNAPSHOT)
    X = np.array(snap['positions']); O = np.array(pay['old_positions']); V = np.array(pay['positions'])
    d, near = cKDTree(O).query(X)
    if d.max() > 1e-3: raise RuntimeError('BareArmsV7 no longer matches the M4 V9 source (%.4f cm)' % d.max())
    key = lambda p: tuple(np.round(p, 4))
    # Split vertices share a position; overrides and shapes are keyed by welded position.
    weights = {}
    for i, vid in enumerate(pay['vertex_ids']):
        w = pay['weights'].get(str(vid))
        if w: weights[key(O[i])] = w
    W = [weights.get(key(O[j]), w) for j, w in zip(near, snap['weights'])]
    index = {vid: i for i, vid in enumerate(pay['vertex_ids'])}
    shapes = {}
    for name, rows in pay['morphs'].items():
        disp = {}
        for row in rows:
            i = index[row[0]]; disp[key(O[i])] = np.array(row[1:4]) - V[i]
        shapes[name] = np.array([disp.get(key(O[j]), np.zeros(3)) for j in near])
    # Per-corner UVs follow the matching M4 triangle, corner by corner.
    T = np.array(snap['triangles']); MT = np.array(m4['triangles'])
    _, tri = cKDTree(O[MT].mean(axis=1)).query(X[T].mean(axis=1))
    UV = np.zeros((len(T), 3, 2)); src = np.array(pay['uv0'])
    for k, (t, j) in enumerate(zip(T, tri)):
        corners = O[MT[j]]
        for c in range(3): UV[k, c] = src[j, np.argmin(np.linalg.norm(corners - X[t[c]], axis=1))]
    return {'snapshot': snap, 'X': V[near], 'T': T, 'UV': UV, 'W': W, 'shapes': shapes}
