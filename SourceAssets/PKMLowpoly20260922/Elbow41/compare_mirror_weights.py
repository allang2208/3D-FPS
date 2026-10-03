"""Is the left arm skinned the same as the right?

The mesh is mirrored: two loose parts, identical topology, bboxes mirror images.
The right arm deforms smoothly in the idle and the left does not, so compare the
weight vectors of mirrored vertex pairs with _l/_r swapped.  Any vertex whose
weights differ is a candidate for the visible ridge.
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow41'

d = np.load(ROOT / 'Elbow39' / 'v7_mesh.npz', allow_pickle=True)
V = d['verts'].astype(np.float64)
WIDX, WVAL = d['w_idx'], d['w_val'].astype(np.float64)
BONES = list(d['bones'])
NB = len(BONES)


def swap(name):
    if name.endswith('_l'):
        return name[:-2] + '_r'
    if name.endswith('_r'):
        return name[:-2] + '_l'
    return name


R2L = np.array([BONES.index(swap(n)) if swap(n) in BONES else -1 for n in BONES])
L2R = np.array([BONES.index(swap(n)) if swap(n) in BONES else -1 for n in BONES])

W = np.zeros((len(V), NB))
for k in range(WIDX.shape[1]):
    idx, w = WIDX[:, k], WVAL[:, k]
    act = (idx >= 0) & (w > 0)
    np.add.at(W, (np.where(act)[0], idx[act]), w[act])

left = np.where(V[:, 0] < 0)[0]
right = np.where(V[:, 0] > 0)[0]
print('left verts %d  right verts %d' % (len(left), len(right)))

# mirror the right arm onto the left
Rm = V[right].copy()
Rm[:, 0] *= -1.0
from scipy.spatial import cKDTree  # noqa: E402

tree = cKDTree(V[left])
dist, nn = tree.query(Rm, k=1)
print('mirror match: mean %.6f m  max %.6f m  (pairs within 1 mm: %d/%d)'
      % (dist.mean(), dist.max(), int((dist < 1e-3).sum()), len(right)))

# weights of the mirrored right arm, expressed in left-bone names
Wr = W[right]
Wr_sw = np.zeros_like(Wr)
for j in range(NB):
    if R2L[j] >= 0:
        Wr_sw[:, R2L[j]] += Wr[:, j]

Wl = W[left][nn]
diff = np.abs(Wl - Wr_sw)
per_vertex = diff.sum(axis=1)
print('\nper-vertex |dW| across mirrored pairs:')
print('  mean %.4f  median %.4f  p95 %.4f  p99 %.4f  max %.4f'
      % (per_vertex.mean(), np.median(per_vertex),
         np.percentile(per_vertex, 95), np.percentile(per_vertex, 99),
         per_vertex.max()))

# which bones account for the mismatch
bone_diff = diff.sum(axis=0)
order = np.argsort(-bone_diff)[:14]
print('\nbones carrying the mismatch (sum |dW| over all mirrored pairs):')
for i in order:
    if bone_diff[i] <= 0:
        continue
    print('  %-26s %8.2f   left mean %.4f  right(mirrored) mean %.4f'
          % (BONES[i], bone_diff[i], Wl[:, i].mean(), Wr_sw[:, i].mean()))

# where are the worst vertices
worst = np.argsort(-per_vertex)[:15]
print('\nworst mismatched vertices (left-arm coordinates):')
for k in worst:
    v = V[left][nn[k]]
    top = np.argsort(-diff[k])[:3]
    print('  |dW| %.3f at (%.3f, %.3f, %.3f)  mirror-dist %.5f  %s'
          % (per_vertex[k], v[0], v[1], v[2], dist[k],
             ', '.join('%s %+.3f' % (BONES[i], Wl[k, i] - Wr_sw[k, i]) for i in top)))

# how much of the mismatch sits in the forearm band
e_rest = d['rest'][BONES.index('lowerarm_l')][:3, 3]
s_rest = d['rest'][BONES.index('upperarm_l')][:3, 3]
w_rest = d['rest'][BONES.index('hand_l')][:3, 3]
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
flen = float(np.linalg.norm(w_rest - e_rest))
pv = V[left][nn] - e_rest
t = pv @ f0 / flen
rad = np.linalg.norm(pv - np.outer(t * flen, f0), axis=1)
arm = rad < 0.075
for lo, hi, tag in ((-1.0, -0.2, 'upper arm'), (-0.2, 0.2, 'elbow'),
                    (0.2, 0.9, 'forearm'), (0.9, 3.0, 'hand/wrist')):
    sel = arm & (t >= lo) & (t < hi)
    if sel.sum():
        print('  band %-11s n=%5d  mean|dW| %.4f  max %.4f'
              % (tag, int(sel.sum()), per_vertex[sel].mean(), per_vertex[sel].max()))

np.save(HERE / 'mirror_weight_diff.npy', per_vertex)
(HERE / 'mirror_weight_report.json').write_text(json.dumps({
    'mirror_mean_m': float(dist.mean()), 'mirror_max_m': float(dist.max()),
    'per_vertex_mean': float(per_vertex.mean()),
    'per_vertex_p99': float(np.percentile(per_vertex, 99)),
    'per_vertex_max': float(per_vertex.max()),
}, indent=2), encoding='utf-8')
print('\nMIRROR_WEIGHT_DONE')