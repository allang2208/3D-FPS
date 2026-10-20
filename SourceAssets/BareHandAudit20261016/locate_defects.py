"""Locate the individual master defects reported by audit_mesh.py (read-only)."""
import json, sys
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from audit_mesh import side_and_region

d = json.loads(Path(sys.argv[1]).read_text())
v = np.asarray(d['positions']); t = np.asarray(d['triangles']); n = np.asarray(d['normals']); uv = np.asarray(d['uv'])
m = np.asarray(d['triangle_materials']); W = d['weights']
cross = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
area = .5 * np.linalg.norm(cross, axis=1)
gn = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
dots = np.einsum('ij,ij->i', gn, n.mean(1))
convention = np.sign(np.median(dots))
def where(ti):
    ws = Counter()
    for vi in t[ti]:
        ws.update(W[vi])
    return '/'.join(side_and_region(dict(ws)))
print('normal/winding convention', convention)
odd = np.where(dots * convention < 0)[0]
print('faces whose stored normal disagrees with the majority winding:', [(int(i), where(i), int(m[i]), round(float(area[i]), 5)) for i in odd])
deg = np.where(area < 1e-6)[0]
print('degenerate faces:', [(int(i), where(i), int(m[i]), t[i].tolist()) for i in deg])
edges = defaultdict(list)
for ti, (a, b, c) in enumerate(t.tolist()):
    for x, y in ((a, b), (b, c), (c, a)):
        edges[(min(x, y), max(x, y))].append((ti, x, y))
bad = [(k, r) for k, r in edges.items() if len(r) == 2 and r[0][1] == r[1][1]]
faces = sorted({ti for _, r in bad for ti, _, _ in r})
print('faces on inconsistent-winding edges:', [(int(i), where(i), int(m[i]), round(float(area[i]), 4), round(float(dots[i] * convention), 3)) for i in faces])
# Texel-density outliers per region
uvc = (uv[:, 1, 0] - uv[:, 0, 0]) * (uv[:, 2, 1] - uv[:, 0, 1]) - (uv[:, 2, 0] - uv[:, 0, 0]) * (uv[:, 1, 1] - uv[:, 0, 1])
for mat in np.unique(m):
    sel = np.where((m == mat) & (np.abs(uvc) > 1e-10) & (area > 1e-6))[0]
    r = np.sqrt(area[sel] / (.5 * np.abs(uvc[sel]))); med = np.median(r)
    lo = sel[r < med / 3]; hi = sel[r > med * 3]
    print('material', int(mat), 'median cm/uv %.1f' % med, 'dense(<1/3):', Counter(where(i) for i in lo).most_common(8),
          '| stretched(>3x):', Counter(where(i) for i in hi).most_common(8))
    print('   uv bbox of dense faces:', np.round(uv[lo].reshape(-1, 2).min(0), 3).tolist() if len(lo) else None,
          np.round(uv[lo].reshape(-1, 2).max(0), 3).tolist() if len(lo) else None)
print('material regions:', {int(mat): Counter(where(i) for i in np.where(m == mat)[0][::25]).most_common(6) for mat in np.unique(m)})
