"""Wrist-ring weight denoise (offline). Writes Work/weights.json.

The old hand/forearm split leaves a kink in the weight gradient (continuous, not smooth), which folds
into a ridge whenever the wrist bends. Inside +-2.2 cm of that line only, the weight vectors are
averaged with their neighbours (welded topology); bone set, per-vertex sum and everything outside the
band are unchanged. This is a local denoise, not a redistribution of the forearm.
"""
import json
import numpy as np
from scipy.spatial import cKDTree
from m4data import M4, R

m = M4(); wv = m.weld; nb = m.welded_adjacency(); P = np.load(R / 'Work/geometry.npz')['welded']
W = [None] * m.nw
for v in range(len(m.X)):
    if W[wv[v]] is None: W[wv[v]] = dict(m.W[v])
def seam(a, b):
    sa = {wv[v] for ti, t in enumerate(m.T) if m.region[ti] == a for v in t}
    return sa & {wv[v] for ti, t in enumerate(m.T) if m.region[ti] == b for v in t}


ring = seam(1, 2) | seam(0, 1)                         # wrist split and the V6 upper-arm join above the elbow
d = cKDTree(P[sorted(ring)]).query(P)[0]
band = np.nonzero(d < 2.2)[0]
alpha = 1 - np.clip((d - .8) / 1.4, 0, 1); alpha = alpha * alpha * (3 - 2 * alpha)
bones = sorted({b for i in band for b in W[i]} | {b for i in band for n in nb[i] for b in W[n]})
bi = {b: k for k, b in enumerate(bones)}
M = np.zeros((m.nw, len(bones)))
for i in range(m.nw):
    for b, x in W[i].items():
        if b in bi: M[i, bi[b]] = x
orig = M.copy()
for _ in range(10):
    new = M.copy()
    for i in band: new[i] = (1 - .5 * alpha[i]) * M[i] + .5 * alpha[i] * M[list(nb[i])].mean(axis=0)
    M = new
changed = {}
for i in band:
    row = {b: float(M[i, bi[b]]) for b in bones if M[i, bi[b]] > 1e-4}
    s = sum(row.values()); outside = {b: x for b, x in W[i].items() if b not in bi}
    total = s + sum(outside.values())
    row = {b: x / total for b, x in {**row, **outside}.items()}
    if max(abs(row.get(b, 0) - W[i].get(b, 0)) for b in set(row) | set(W[i])) > 1e-3: changed[int(i)] = row
delta = max(max(abs(r.get(b, 0) - W[i].get(b, 0)) for b in set(r) | set(W[i])) for i, r in changed.items())
(R / 'Work/weights.json').write_text(json.dumps(dict(changed=changed, band_vertices=int(len(band)), max_change=delta, bones=bones)))
print('WEIGHTS band %d changed %d max weight change %.3f bones %s' % (len(band), len(changed), delta, bones))
