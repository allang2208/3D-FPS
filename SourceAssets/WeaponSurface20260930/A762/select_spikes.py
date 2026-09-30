"""Select the Meshy cut-border spike triangles on the current A762 mesh (plain CPython).

Works on inspect/geometry/A762_AfterSurface.bin, whose triangle order equals a fresh
Geometry Script copy of the runtime asset. A spike tip is a vertex of a Meshy-generated
slot whose incident corner angles sum below 70 degrees while an incident edge is much
longer than that slot's median edge; the thin triangles touching such tips (longest
edge^2 / (2*area) > 6) are the teeth. Rebuilt parts and the arms are never touched.
Writes Bake/spike_selection.json (triangle positions in dump order + centroids).
"""
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import measure_references as M  # noqa: E402

MESHY = ['M_A762_Receiver', 'M_A762_Trigger', 'M_A762_Bolt', 'M_A762_FactoryRearGrip']
h, pos, tri, mat, uv, nrm = M.read_geometry(M.GEOMETRY / 'A762_AfterSurface.bin')
P = pos[tri].astype(np.float64)
V = len(pos)
area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
el = np.stack([np.linalg.norm(P[:, 1] - P[:, 0], axis=1), np.linalg.norm(P[:, 2] - P[:, 1], axis=1),
               np.linalg.norm(P[:, 0] - P[:, 2], axis=1)], 1)
thin = el.max(1) ** 2 / np.maximum(2 * area, 1e-12)


def angle(a, b, c):
    x, y = b - a, c - a
    return np.arccos(np.clip(np.einsum('ij,ij->i', x, y) / np.maximum(np.linalg.norm(x, axis=1) * np.linalg.norm(y, axis=1), 1e-12), -1, 1))


angle_sum = np.zeros(V)
for k in range(3):
    np.add.at(angle_sum, tri[:, k], angle(P[:, k], P[:, (k + 1) % 3], P[:, (k + 2) % 3]))
vmax = np.zeros(V)
for k in range(3):
    np.maximum.at(vmax, tri[:, k], el[:, k])
    np.maximum.at(vmax, tri[:, (k + 1) % 3], el[:, k])
# Open-boundary edges (cut borders): an edge used by exactly one triangle.
E = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
ekey = E[:, 0].astype(np.int64) * V + E[:, 1]
_, inv, cnt = np.unique(ekey, return_inverse=True, return_counts=True)
on_border = (cnt[inv] == 1).reshape(3, -1).any(0)
border_vertex = np.zeros(V, bool)
border_vertex[E[cnt[inv] == 1].ravel()] = True
selected, report = [], {}
for name in MESHY:
    idx = h['slots'].index(name)
    sel = np.nonzero(mat == idx)[0]
    med = float(np.median(el[sel]))
    verts = np.unique(tri[sel])
    tips = verts[(np.degrees(angle_sum[verts]) < 70) & (vmax[verts] > max(4 * med, 0.3))]
    # Teeth sit on the cut border: needle triangles that touch a spike tip and the border.
    touches_border = border_vertex[tri[sel]].any(1)
    teeth = sel[np.isin(tri[sel], tips).any(1) & (thin[sel] > 6) & touches_border]
    selected.extend(teeth.tolist())
    c = P[teeth].mean(1) if len(teeth) else np.zeros((0, 3))
    report[name] = {'triangles': int(len(sel)), 'tips': int(len(tips)), 'teeth': int(len(teeth)),
                    'teeth_area_cm2': round(float(area[teeth].sum()), 3), 'slot_area_cm2': round(float(area[sel].sum()), 2),
                    'bbox': [round(float(x), 2) for x in (*c.min(0), *c.max(0))] if len(teeth) else None}
    print(name.ljust(26), report[name], flush=True)
selected = sorted(set(selected))
centroids = P[selected].mean(1)
out = {'source': 'inspect/geometry/A762_AfterSurface.bin', 'triangle_count': int(len(tri)),
       'position_checksum': float(np.abs(pos.astype(np.float64)).sum()),
       'delete': selected, 'centroid_checksum': float((centroids @ np.array([1.0, 2.0, 3.0])).sum()),
       'centroids': np.round(centroids, 4).tolist(),
       'per_slot': report}
(HERE / 'Bake' / 'spike_selection.json').write_text(json.dumps(out), encoding='utf-8')
print('SPIKES_SELECTED', len(selected), 'area cm2', round(float(area[selected].sum()), 2))
