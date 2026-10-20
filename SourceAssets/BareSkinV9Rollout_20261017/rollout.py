"""Shared offline data for the V9 rollout: the accepted M4 V9 sample and the snapshotted targets.

Canonical space = the M4 viewmodel reference pose (the V7 master was authored in it). Every target was
derived from the master by blending per-bone transforms with its own skin weights, so a target vertex
maps back with the inverse of the same blend built from the two reference skeletons.
"""
import json, hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'; S9 = P / 'SourceAssets/BareSkinV9M4_20261017'
M4_PATH = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'


def key_of(pk): return hashlib.sha256(pk.split('.')[0].encode()).hexdigest()[:12]


def load_snapshot(pk): return json.loads((R / 'Snapshots' / (key_of(pk) + '.json')).read_text())


def bone_mats(bones):
    out = {}
    for n, b in bones.items():
        m = np.eye(4); m[:3, :3] = Rot.from_quat(b['q']).as_matrix(); m[:3, 3] = b['t']; out[n] = m
    return out


class M4Source:
    """M4 V8 (pre-V9) rest data in M4 triangle order plus every V9 result, all per split vertex / corner."""
    def __init__(self):
        import sys; sys.path.insert(0, str(S9))
        from m4data import M4
        m = M4(); self.m = m; wv = m.weld
        g = np.load(S9 / 'Work/geometry.npz')
        self.X8 = m.X; self.T = m.T; self.N8 = m.N; self.UV8 = m.UV; self.W8 = m.W; self.region = m.region; self.weld = wv
        self.X9 = g['welded'][wv]; self.N9 = np.load(S9 / 'Work/normals.npy'); self.UV9 = np.load(S9 / 'Work/uv_new.npy')
        self.refit = set(g['refit'].tolist()) if 'refit' in g.files else set()
        ch = {int(k): v for k, v in json.loads((S9 / 'Work/weights.json').read_text())['changed'].items()}
        self.W9 = [ch.get(wv[v], m.W[v]) for v in range(len(m.X))]
        snap = load_snapshot(M4_PATH); self.bones = snap['bones']; self.B = bone_mats(snap['bones'])
        self.tree = cKDTree(self.X8)
        self.cent = self.X8[self.T].mean(axis=1); self.ctree = cKDTree(self.cent)


def bone_alias(name, have):
    """Target bone -> M4 bone with the same role (native rigs rename or drop a few bones)."""
    if name in have: return name
    side = name[-1]
    if name.startswith('lowerarm_aux_'): return 'lowerarm_' + side
    if '_twist_' in name: return name.split('_twist_')[0] + '_' + side
    return None


def canonical(tgt, src):
    """Per target vertex: the blended (target ref -> M4 ref) transform and the canonical position."""
    Bt = bone_mats(tgt['bones']); X = np.array(tgt['positions'])
    L = np.zeros((len(X), 4, 4)); miss = 0
    for v, row in enumerate(tgt['weights']):
        tot = 0
        for b, w in row.items():
            mb = bone_alias(b, src.B)
            if mb is None or b not in Bt: miss += w; continue
            L[v] += w * (src.B[mb] @ np.linalg.inv(Bt[b])); tot += w
        if tot > 0: L[v] /= tot
        else: L[v] = np.eye(4)
    Xc = np.einsum('vij,vj->vi', L, np.c_[X, np.ones(len(X))])[:, :3]
    return Xc, L, miss
