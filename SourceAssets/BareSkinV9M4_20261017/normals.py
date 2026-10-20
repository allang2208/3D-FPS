"""Final per-corner normals for the V9 rest shape. Writes Work/normals.npy (snapshot corner order).

The accepted authored normals are kept and rotated by the local change of the geometric normal, so
untouched areas shade exactly as before. Inside the old wrist split the geometric normal of the
smoothed surface is used (one value per welded vertex), which removes the ring.
"""
import numpy as np
from scipy.spatial import cKDTree
from m4data import M4, R

m = M4(); wv = m.weld; g = np.load(R / 'Work/geometry.npz'); P1 = g['welded']; P0 = np.zeros_like(P1); P0[wv] = m.X


def geo(Pw):
    tw = wv[m.T]; a, b, c = Pw[tw[:, 0]], Pw[tw[:, 1]], Pw[tw[:, 2]]
    fn = np.cross(b - a, c - a); fn *= np.sign(np.einsum('ij,ij->', fn, m.N.mean(axis=1)))
    acc = np.zeros_like(Pw)
    for k, (p, q, r) in enumerate(((a, b, c), (b, c, a), (c, a, b))):        # angle-weighted
        u = q - p; v = r - p
        ang = np.arccos(np.clip(np.einsum('ij,ij->i', u, v) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-12), -1, 1))
        np.add.at(acc, tw[:, k], fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12) * ang[:, None])
    return acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)


G0, G1 = geo(P0), geo(P1)
orig = np.zeros_like(P1)
for k in range(3): np.add.at(orig, wv[m.T[:, k]], m.N[:, k])
orig /= np.maximum(np.linalg.norm(orig, axis=1, keepdims=True), 1e-12)


def rotate(v, a, b):
    """Rotate v by the rotation taking unit a to unit b (row-wise)."""
    axis = np.cross(a, b); s = np.linalg.norm(axis, axis=1); c = np.einsum('ij,ij->i', a, b)
    k = axis / np.maximum(s, 1e-12)[:, None]
    return v * c[:, None] + np.cross(k, v) * s[:, None] + k * np.einsum('ij,ij->i', k, v)[:, None] * (1 - c)[:, None]


moved = np.linalg.norm(P1 - P0, axis=1) > .002            # untouched vertices keep the authored normal exactly
turn = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', G0, G1), -1, 1)))
target = np.where((turn > 20)[:, None], G0 + (G1 - G0) * (20 / np.maximum(turn, 1e-9))[:, None], G1)   # cap unstable sliver turns
target /= np.linalg.norm(target, axis=1, keepdims=True)
n = np.where(moved[:, None], rotate(orig, G0, target), orig)
def seam(a, b):
    sa = {wv[v] for ti, t in enumerate(m.T) if m.region[ti] == a for v in t}
    return sa & {wv[v] for ti, t in enumerate(m.T) if m.region[ti] == b for v in t}


ring = seam(1, 2) | seam(0, 1)
d = cKDTree(P1[sorted(ring)]).query(P1)[0]
w = 1 - np.clip((d - .6) / 1.6, 0, 1); w = w * w * (3 - 2 * w)
if 'refit' in g.files and len(g['refit']): w[g['refit']] = 1.0    # untangled fold-overs: geometric normal only
n = n * (1 - w)[:, None] + G1 * w[:, None]; n /= np.linalg.norm(n, axis=1, keepdims=True)
corner = n[wv[m.T]]
np.save(R / 'Work/normals.npy', corner)
dev = np.degrees(np.arccos(np.clip(np.einsum('ijk,ijk->ij', corner, m.N), -1, 1)))
print('NORMALS changed corners >2deg %d  >5deg %d  max %.1f  ring-band vertices %d' % ((dev > 2).sum(), (dev > 5).sum(), dev.max(), int((w > 0).sum())))
