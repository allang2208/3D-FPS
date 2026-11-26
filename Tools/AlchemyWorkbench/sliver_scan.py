"""Find degenerate sliver triangles in the deployed arm mesh.

The workbench fold fix cannot change any vertex because every skin influence
lives on the 24 arm/hand bones (verified from install_payload.json). So if the
line comes from the arm mesh it must be a sliver *inside* the arm chain --
geometry that stretches thin when the two hands separate during pour/dip.

A sliver has a huge longest-edge-to-height ratio, or an edge far longer than
the local surface. Scan the actual V9 geometry for both.
"""
from pathlib import Path
import numpy as np

Z = np.load(Path(__file__).resolve().parents[2] / "SourceAssets/BareSkinV9M4_20261017/Work/mesh.npz",
            allow_pickle=True)
X = Z['X'].astype(np.float64)      # (N,3) -- metres, most likely
T = Z['T'].astype(np.int64)        # (M,3)
print('verts', X.shape, 'tris', T.shape)
print('bbox min', np.round(X.min(0), 4), 'max', np.round(X.max(0), 4))
print('extent (units)', np.round(X.max(0) - X.min(0), 4))

A, B, C = X[T[:, 0]], X[T[:, 1]], X[T[:, 2]]
e0, e1, e2 = B - A, C - A, C - B
l0 = np.linalg.norm(e0, axis=1)
l1 = np.linalg.norm(e1, axis=1)
l2 = np.linalg.norm(e2, axis=1)
L = np.stack([l0, l1, l2], axis=1)
longest = L.max(axis=1)
shortest = L.min(axis=1)

area = 0.5 * np.linalg.norm(np.cross(e0, e1), axis=1)
with np.errstate(divide='ignore', invalid='ignore'):
    height = 2.0 * area / np.where(longest > 0, longest, np.nan)
    aspect = longest / np.where(height > 0, height, np.nan)

print('\nedge length percentiles (units):')
for q in (50, 90, 99, 99.9, 100):
    print('   p%-5s longest=%.5f' % (q, np.percentile(longest, q)))

print('\nworst 12 triangles by aspect ratio:')
order = np.argsort(-np.nan_to_num(aspect, nan=0.0))[:12]
for i in order:
    print('   tri %6d  aspect=%9.1f  longest=%.5f  area=%.3e  verts %s %s %s'
          % (i, aspect[i], longest[i], area[i],
             np.round(A[i], 3), np.round(B[i], 3), np.round(C[i], 3)))

print('\ntriangles with longest edge > 0.05 (i.e. >5 units of 1cm if cm):')
big = np.where(longest > 0.05)[0]
print('   count', len(big))
if len(big):
    for i in big[:10]:
        print('   tri %6d longest=%.4f aspect=%.1f at %s'
              % (i, longest[i], aspect[i], np.round(A[i], 3)))

print('\ntriangles with area ~ 0 (degenerate):')
deg = np.where(area < 1e-12)[0]
print('   count', len(deg))
