"""Blender (background): pick the visible cut-border teeth of the Meshy A762 receiver parts.

blender -b A762_SurfaceBake.blend -P select_teeth.py

The Meshy receiver, trigger and bolt were cut when the magazine, upper receiver and
front were rebuilt; the cut left saw-tooth slivers along the open borders. A tooth here
is a triangle of those slots that (a) lies within two rings of an open border, (b) is a
sliver (longest edge^2 / (2*area) > 3), and (c) is actually seen from outside
(first hit of orthographic rays from 642 directions). The grip is excluded: its border
triangles lie on its visible surface. Writes Bake/teeth_selection.json with UE-space
centroids (Blender Y is mirrored) so the UE script can match triangles exactly.
"""
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).parent
SLOTS = ('M_A762_Receiver', 'M_A762_Trigger', 'M_A762_Bolt')
ob = bpy.data.objects['A762_BAKE']
me = ob.data
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
tri = co[corner]
area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
el = np.stack([np.linalg.norm(tri[:, (k + 1) % 3] - tri[:, k], axis=1) for k in range(3)], 1)
thin = el.max(1) ** 2 / np.maximum(2 * area, 1e-12)

E = np.sort(np.concatenate([corner[:, [0, 1]], corner[:, [1, 2]], corner[:, [2, 0]]]), axis=1)
key = E[:, 0].astype(np.int64) * V + E[:, 1]
_, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
border_v = np.zeros(V, bool)
border_v[E[cnt[inv] == 1].ravel()] = True
ring1 = border_v[corner].any(1)
ring_v = border_v.copy()
ring_v[corner[ring1].ravel()] = True
ring2 = ring_v[corner].any(1)

tree = BVHTree.FromPolygons([tuple(p) for p in co], corner.tolist(), all_triangles=True)
lo, hi = co.min(0), co.max(0)
center = Vector(((lo + hi) / 2).tolist())
radius = float(np.linalg.norm(hi - lo) / 2) * 1.05
seen = np.zeros(F, bool)
n_dirs, grid = 642, 140
golden = math.pi * (3 - math.sqrt(5))
for i in range(n_dirs):
    y = 1 - 2 * (i + 0.5) / n_dirs
    r = math.sqrt(1 - y * y)
    d = Vector((math.cos(golden * i) * r, y, math.sin(golden * i) * r))
    u = d.orthogonal().normalized()
    v = d.cross(u)
    for a in np.linspace(-radius, radius, grid):
        for b in np.linspace(-radius, radius, grid):
            hit, _, index, _ = tree.ray_cast(center - d * radius * 2 + u * a + v * b, d, radius * 4)
            if hit is not None:
                seen[index] = True

slot_ids = [names.index(s) for s in SLOTS if s in names]
# Zone of the reported defect (UE cm): magazine-well junction and the upper-receiver joint
# above it. Blender Y is mirrored, so the UE range y in [-33.8, -14.5] becomes [14.5, 33.8].
c_all = tri.mean(1)
zone = (c_all[:, 1] > 14.5) & (c_all[:, 1] < 33.8) & (c_all[:, 2] > -10.7) & (c_all[:, 2] < -6.3)
# A tooth is a free-standing fin: nothing within FIN_REACH on either side of it. Real
# receiver walls always have the opposite wall, the magazine or an inner part behind them.
FIN_REACH = 5.0
fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-12)[:, None]
fin = np.zeros(F, bool)
candidates = np.nonzero(np.isin(mats, slot_ids) & zone & ring2 & seen)[0]
for i in candidates:
    c = Vector(c_all[i].tolist())
    n = Vector(fn[i].tolist())
    free = True
    for s in (1.0, -1.0):
        hit = tree.ray_cast(c + n * (0.01 * s), n * s, FIN_REACH)[0]
        if hit is not None:
            free = False
            break
    fin[i] = free
pick = fin
cent = tri[pick].mean(1) * np.array([1.0, -1.0, 1.0])  # back to UE coordinates
report = {s: int((pick & (mats == names.index(s))).sum()) for s in SLOTS}
report_area = {s: round(float(area[pick & (mats == names.index(s))].sum()), 3) for s in SLOTS}
out = {'rule': 'ring2 of open border & sliver>3 & seen from outside; slots ' + ', '.join(SLOTS),
       'count': int(pick.sum()), 'area_cm2': round(float(area[pick].sum()), 3), 'per_slot': report,
       'per_slot_area_cm2': report_area, 'centroids': np.round(cent, 4).tolist()}
(HERE / 'Bake' / 'teeth_selection.json').write_text(json.dumps(out), encoding='utf-8')
print('A762_TEETH', out['count'], out['area_cm2'], report, report_area, flush=True)
