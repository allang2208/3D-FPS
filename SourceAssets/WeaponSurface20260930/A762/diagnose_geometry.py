"""A762 geometry diagnosis (plain CPython): spikes, and before/after surface install.

1. Before vs after: inspect/geometry/A762.bin was dumped before any surface-standard
   write; A762_AfterSurface.bin is the current runtime mesh. Compares vertex sets,
   triangle connectivity (as sorted corner positions), material ids and triangle areas.
2. Spikes: triangles whose longest edge is far above the local edge scale of their
   slot and that are needle-thin, plus vertices far from all of their neighbours.
Writes Bake/geometry_diagnosis.json.
"""
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import measure_references as M  # noqa: E402

out = {}
h0, p0, t0, m0, uv0, n0 = M.read_geometry(M.GEOMETRY / 'A762.bin')
after = M.GEOMETRY / 'A762_AfterSurface.bin'
if after.exists():
    h1, p1, t1, m1, uv1, n1 = M.read_geometry(after)

    def tri_keys(pos, tri):
        c = np.round(pos[tri].astype(np.float64), 3)
        # Order the three corners canonically, then sort triangles.
        idx = np.lexsort((c[:, :, 2], c[:, :, 1], c[:, :, 0]))
        c = np.take_along_axis(c, idx[:, :, None], axis=1).reshape(len(tri), 9)
        return c

    k0, k1 = tri_keys(p0, t0), tri_keys(p1, t1)
    s0 = np.lexsort(k0.T[::-1]); s1 = np.lexsort(k1.T[::-1])
    same_shape = k0.shape == k1.shape
    identical = bool(same_shape and np.array_equal(k0[s0], k1[s1]))
    mat_same = bool(same_shape and identical and np.array_equal(m0[s0], m1[s1]))
    a0 = 0.5 * np.linalg.norm(np.cross(p0[t0][:, 1] - p0[t0][:, 0], p0[t0][:, 2] - p0[t0][:, 0]), axis=1)
    a1 = 0.5 * np.linalg.norm(np.cross(p1[t1][:, 1] - p1[t1][:, 0], p1[t1][:, 2] - p1[t1][:, 0]), axis=1)
    out['before_vs_after'] = {
        'vertices': [int(len(p0)), int(len(p1))], 'triangles': [int(len(t0)), int(len(t1))],
        'vertex_set_identical': bool(len(p0) == len(p1) and np.allclose(np.sort(p0, 0), np.sort(p1, 0), atol=1e-4)),
        'triangle_connectivity_identical': identical, 'material_ids_identical': mat_same,
        'total_area_cm2': [round(float(a0.sum()), 3), round(float(a1.sum()), 3)],
        'max_triangle_area_cm2': [round(float(a0.max()), 4), round(float(a1.max()), 4)],
    }
    if not identical and same_shape:
        diff = np.any(np.abs(k0[s0] - k1[s1]) > 1e-3, axis=1)
        out['before_vs_after']['differing_triangles'] = int(diff.sum())
    print('BEFORE_VS_AFTER', out['before_vs_after'], flush=True)

# Spike search on the pre-install mesh (identical geometry if the comparison above holds).
P = p0[t0].astype(np.float64)
e = np.stack([np.linalg.norm(P[:, 1] - P[:, 0], axis=1), np.linalg.norm(P[:, 2] - P[:, 1], axis=1),
              np.linalg.norm(P[:, 0] - P[:, 2], axis=1)], 1)
area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
longest = e.max(1)
thin = longest ** 2 / np.maximum(2 * area, 1e-9)  # ~ longest edge / height
spikes = {}
for i, name in enumerate(h0['slots']):
    sel = np.nonzero(m0 == i)[0]
    if not len(sel) or 'Manny' in name:
        continue
    med = float(np.median(longest[sel]))
    cand = sel[(longest[sel] > max(6 * med, 0.4)) & (thin[sel] > 12)]
    if len(cand):
        c = P[cand].reshape(-1, 3)
        spikes[name] = {'count': int(len(cand)), 'median_edge_cm': round(med, 3),
                        'longest_cm': round(float(longest[cand].max()), 2),
                        'bbox': [round(float(x), 2) for x in (*c.min(0), *c.max(0))],
                        'triangles': cand[:400].tolist()}
out['needle_triangles'] = spikes
for k, v in spikes.items():
    print('NEEDLES', k.ljust(30), {x: v[x] for x in v if x != 'triangles'})

out['slot_bbox'] = {}
for i, name in enumerate(h0['slots']):
    sel = m0 == i
    if sel.any():
        q = P[sel].reshape(-1, 3)
        out['slot_bbox'][name] = [round(float(x), 2) for x in (*q.min(0), *q.max(0))]
(HERE / 'Bake' / 'geometry_diagnosis.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('DIAGNOSIS_WRITTEN')
