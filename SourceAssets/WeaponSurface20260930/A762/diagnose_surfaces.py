"""Blender (background): find see-through faces and spike tips on the A762 gun.

blender -b A762_SurfaceBake.blend -P diagnose_surfaces.py

Uses the arm-free bake copy (A762_BAKE), whose faces map 1:1 to the gun triangles of
the runtime mesh (same order after the arm triangles are removed, see face_map below).
- Back-facing first hits: orthographic rays from 642 directions; a first hit whose
  geometric normal faces away from the viewer is culled by the single-sided material,
  so the player sees through it (white floor/sky behind).
- Open boundary edges: edges with one face, i.e. real holes or cut borders.
- Spike tips: vertices whose incident corner angles sum below 70 degrees and whose
  incident edges are long compared with the slot's median edge.
Writes Bake/surface_diagnosis.json with per-slot counts, bounding boxes and the
original runtime triangle indices of each finding.
"""
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).parent
report = json.loads((HERE / 'Bake' / 'bake_report.json').read_text(encoding='utf-8'))
ob = bpy.data.objects['A762_BAKE']
me = ob.data
me.update()
V, F = len(me.vertices), len(me.polygons)
co = np.empty(V * 3, np.float32)
me.vertices.foreach_get('co', co)
co = co.reshape(V, 3).astype(np.float64)
corner = np.empty(F * 3, np.int32)
me.loops.foreach_get('vertex_index', corner)
corner = corner.reshape(F, 3)
mats = np.empty(F, np.int32)
me.polygons.foreach_get('material_index', mats)
names = [m.name.replace('BAKE_', '') for m in me.materials]

# Bake copy faces are the runtime gun triangles in dump order, with arm triangles removed.
slots = report['objects']['A762']['slots']
import sys
sys.path.insert(0, str(HERE.parent))
with open(HERE.parent / 'inspect' / 'geometry' / 'A762.bin', 'rb') as f:
    header = json.loads(f.readline().decode('utf-8'))
    T = header['triangles']
    f.seek(0)
    f.readline()
    raw = f.read()
Vd = header['vertices']
off = Vd * 12 + T * 12
dump_mat = np.frombuffer(raw[off:off + T * 4], np.int32)
arm = np.array([any(k in (m or '') for k in ('Manny', 'BarePalm', 'BareNative', 'BareFamily')) for m in header['materials']])
face_map = np.nonzero(~arm[dump_mat])[0]
assert len(face_map) == F, (len(face_map), F)

tri = co[corner]
fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
area = 0.5 * np.linalg.norm(fn, axis=1)
fn /= np.maximum(2 * area, 1e-12)[:, None]
tree = BVHTree.FromPolygons([tuple(p) for p in co], corner.tolist(), all_triangles=True)
lo, hi = co.min(0), co.max(0)
center = Vector(((lo + hi) / 2).tolist())
radius = float(np.linalg.norm(hi - lo) / 2) * 1.05
front = np.zeros(F, np.int32)
back = np.zeros(F, np.int32)
n_dirs, grid = 642, 110
golden = math.pi * (3 - math.sqrt(5))
for i in range(n_dirs):
    y = 1 - 2 * (i + 0.5) / n_dirs
    r = math.sqrt(1 - y * y)
    d = Vector((math.cos(golden * i) * r, y, math.sin(golden * i) * r))
    u = d.orthogonal().normalized()
    v = d.cross(u)
    dn = np.array(d[:])
    for a in np.linspace(-radius, radius, grid):
        for b in np.linspace(-radius, radius, grid):
            hit, _, index, _ = tree.ray_cast(center - d * radius * 2 + u * a + v * b, d, radius * 4)
            if hit is None:
                continue
            if np.dot(fn[index], dn) > 0:
                back[index] += 1
            else:
                front[index] += 1

# Open boundary edges.
e = np.sort(np.concatenate([corner[:, [0, 1]], corner[:, [1, 2]], corner[:, [2, 0]]]), axis=1)
face_of_edge = np.tile(np.arange(F), 3)
keys = e[:, 0].astype(np.int64) * V + e[:, 1]
uniq, inverse, counts = np.unique(keys, return_inverse=True, return_counts=True)
open_edge = counts[inverse] == 1

# Spike tips: small total corner angle at a vertex with long incident edges.
def corner_angle(a, b, c):
    x, y = b - a, c - a
    return np.arccos(np.clip(np.einsum('ij,ij->i', x, y) / np.maximum(np.linalg.norm(x, axis=1) * np.linalg.norm(y, axis=1), 1e-12), -1, 1))
angle_sum = np.zeros(V)
for k in range(3):
    np.add.at(angle_sum, corner[:, k], corner_angle(tri[:, k], tri[:, (k + 1) % 3], tri[:, (k + 2) % 3]))
edge_len = np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1)
vmax = np.zeros(V)
np.maximum.at(vmax, e[:, 0], edge_len)
np.maximum.at(vmax, e[:, 1], edge_len)

out = {'slots': {}, 'visible_backface_faces': 0}
for idx, name in enumerate(names):
    sel = mats == idx
    if not sel.any():
        continue
    med = float(np.median(edge_len[np.isin(face_of_edge, np.nonzero(sel)[0])]))
    see_through = sel & (back > 0) & (back >= front)
    open_faces = np.unique(face_of_edge[open_edge & sel[face_of_edge]])
    vset = np.unique(corner[sel])
    tips = vset[(np.degrees(angle_sum[vset]) < 70) & (vmax[vset] > max(4 * med, 0.3))]
    tip_faces = np.nonzero(sel & np.isin(corner, tips).any(1))[0]
    entry = {'faces': int(sel.sum()), 'median_edge_cm': round(med, 3),
             'see_through_faces': int(see_through.sum()),
             'see_through_area_cm2': round(float(area[see_through].sum()), 3),
             'open_edge_faces': int(len(open_faces)), 'spike_tips': int(len(tips))}
    if see_through.any():
        q = tri[see_through].reshape(-1, 3)
        entry['see_through_bbox'] = [round(float(x), 2) for x in (*q.min(0), *q.max(0))]
        entry['see_through_runtime_triangles'] = face_map[np.nonzero(see_through)[0]].tolist()
    if len(tips):
        q = co[tips]
        entry['spike_bbox'] = [round(float(x), 2) for x in (*q.min(0), *q.max(0))]
        entry['spike_runtime_triangles'] = face_map[tip_faces].tolist()
        entry['spike_tip_positions'] = [[round(float(x), 2) for x in co[t]] for t in tips[:60]]
    out['slots'][name] = entry
    out['visible_backface_faces'] += entry['see_through_faces']
    print('SURF', name.ljust(30), {k: v for k, v in entry.items() if not isinstance(v, list) or k.endswith('bbox')}, flush=True)
(HERE / 'Bake' / 'surface_diagnosis.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('A762_SURFACE_DIAGNOSIS', out['visible_backface_faces'])
