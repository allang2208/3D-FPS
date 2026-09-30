"""Measure the A762 magazine-well junction on the current runtime mesh (plain CPython).

Prints connected components of the Meshy Bolt/Trigger slots, and per-Y profiles of the
receiver's lower edge, the rebuilt plate (FrontAssembly) and the magazine top, so the
repair (delete remnants, add rebuilt fillers) can be sized from real geometry.
"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import measure_references as M  # noqa: E402

h, pos, tri, mat, uv, nrm = M.read_geometry(M.GEOMETRY / 'A762_AfterSurface.bin')
P = pos[tri].astype(np.float64)
C = P.mean(1)
area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
slot = {n: i for i, n in enumerate(h['slots'])}


def components(sel_tris):
    """Vertex-connected components (positions welded at 1e-4 cm) of a triangle subset."""
    keys = np.round(pos[tri[sel_tris]].reshape(-1, 3) / 1e-4).astype(np.int64)
    _, weld = np.unique(keys, axis=0, return_inverse=True)
    weld = weld.reshape(-1, 3)
    parent = np.arange(weld.max() + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b, c in weld:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[find(rc)] = ra
    roots = np.array([find(a) for a in weld[:, 0]])
    return roots


for name in ('M_A762_Bolt', 'M_A762_Trigger'):
    sel = np.nonzero(mat == slot[name])[0]
    roots = components(sel)
    print('==', name, 'triangles', len(sel), 'components', len(np.unique(roots)))
    rows = []
    for r in np.unique(roots):
        t = sel[roots == r]
        q = P[t].reshape(-1, 3)
        rows.append((area[t].sum(), len(t), q.min(0), q.max(0)))
    for a, n, lo, hi in sorted(rows, key=lambda x: -x[0])[:14]:
        print('   area %.3f tris %5d  x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f' % (a, n, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))

print('== per-Y profile (cm): receiver lowest z left/right, plate lowest z, magazine top z and x span')
rec = mat == slot['M_A762_Receiver']
plate = mat == slot['M_A762_FrontAssembly_Rebuilt']
mag = np.isin(mat, [slot['M_A762_Magazine_Rebuilt'], slot['M_A762_MagazineEdge_Rebuilt'], slot['M_A762_MagazineInside_Rebuilt']])
for y0 in np.arange(-34.0, -12.0, 1.0):
    band = (C[:, 1] >= y0) & (C[:, 1] < y0 + 1.0)
    row = ['y %6.1f' % y0]
    for label, s in (('recL', rec & (C[:, 0] < 5.4)), ('recR', rec & (C[:, 0] >= 5.4))):
        q = C[band & s]
        row.append('%s z>=%6.2f x %5.2f..%5.2f' % (label, q[:, 2].min(), q[:, 0].min(), q[:, 0].max()) if len(q) else '%s   none' % label)
    q = C[band & plate]
    row.append('plate z>=%6.2f' % q[:, 2].min() if len(q) else 'plate none')
    q = P[band & mag].reshape(-1, 3)
    row.append('mag top %6.2f x %5.2f..%5.2f' % (q[:, 2].max(), q[:, 0].min(), q[:, 0].max()) if len(q) else 'mag none')
    print('  '.join(row))
# Receiver side-wall x positions just above the magazine (outer surfaces).
for y0 in (-21.0, -19.0, -17.0, -15.0):
    band = rec & (C[:, 1] >= y0) & (C[:, 1] < y0 + 1.0) & (C[:, 2] < -7.6) & (C[:, 2] > -9.0)
    q = C[band]
    if len(q):
        hist, edges = np.histogram(q[:, 0], bins=np.arange(3.5, 7.6, 0.25))
        print('walls y %.0f x-hist' % y0, ' '.join('%.2f:%d' % (e, n) for e, n in zip(edges, hist) if n))
