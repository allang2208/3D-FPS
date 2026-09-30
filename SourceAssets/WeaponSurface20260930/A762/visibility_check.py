"""Blender (background): baked-mask statistics on externally visible A762 surfaces only.

blender -b A762_SurfaceBake.blend -P visibility_check.py

Hidden shells (Meshy interiors, surfaces covered by rebuilt parts) legitimately bake
to black AO; this separates them from what a player can see. Orthographic rays from
642 directions mark the first-hit faces of the arm-free bake copy; the mask texture
is then read at those faces' UV1 centres. Writes Bake/visibility_stats.json.
"""
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).parent
ob = bpy.data.objects['A762_BAKE']
me = ob.data
deps = bpy.context.evaluated_depsgraph_get()
tree = BVHTree.FromObject(ob, deps)
verts = np.array([v.co[:] for v in me.vertices])
lo, hi = verts.min(0), verts.max(0)
center = Vector(((lo + hi) / 2).tolist())
radius = float(np.linalg.norm(hi - lo) / 2) * 1.05
visible = np.zeros(len(me.polygons), bool)
n_dirs, grid = 642, 96
golden = math.pi * (3 - math.sqrt(5))
for i in range(n_dirs):
    y = 1 - 2 * (i + 0.5) / n_dirs
    r = math.sqrt(1 - y * y)
    d = Vector((math.cos(golden * i) * r, y, math.sin(golden * i) * r))
    u = d.orthogonal().normalized()
    v = d.cross(u)
    for a in np.linspace(-radius, radius, grid):
        for b in np.linspace(-radius, radius, grid):
            origin = center - d * radius * 2 + u * a + v * b
            hit, _, index, _ = tree.ray_cast(origin, d, radius * 4)
            if hit is not None:
                visible[index] = True
img = bpy.data.images.load(str(HERE / 'Bake' / 'T_A762_WS_Mask.png'))
img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.empty(w * h * 4, np.float32)
img.pixels.foreach_get(px)
px = px.reshape(h, w, 4)  # Blender rows start at the bottom (v = 0)
uv = np.empty(len(me.loops) * 2, np.float64)
me.uv_layers['UV1'].data.foreach_get('uv', uv)
uv = uv.reshape(-1, 3, 2).mean(1)
mats = np.empty(len(me.polygons), np.int32)
me.polygons.foreach_get('material_index', mats)
area = np.empty(len(me.polygons), np.float64)
me.polygons.foreach_get('area', area)
x = np.clip((uv[:, 0] * w).astype(int), 0, w - 1)
yv = np.clip((uv[:, 1] * h).astype(int), 0, h - 1)
m = px[yv, x]
out = {'visible_area_share': round(float(area[visible].sum() / area.sum()), 4), 'slots': {}}
for idx, slot in enumerate(me.materials):
    sel = mats == idx
    if not sel.any():
        continue
    vis = sel & visible
    entry = {'area_cm2': round(float(area[sel].sum()), 1), 'visible_share': round(float(area[vis].sum() / max(area[sel].sum(), 1e-9)), 3)}
    if vis.any():
        wts = area[vis] / area[vis].sum()
        for c, name in enumerate(['edge', 'cavity', 'ao']):
            vals = m[vis, c]
            order = np.argsort(vals)
            cdf = np.cumsum(wts[order])
            entry[name + '_p10_50_90'] = [round(float(vals[order][np.searchsorted(cdf, q)]), 3) for q in (0.1, 0.5, 0.9)]
        entry['ao_below_0.3_visible'] = round(float(wts[m[vis, 2] < 0.3].sum()), 3)
        entry['cavity_above_0.5_visible'] = round(float(wts[m[vis, 1] > 0.5].sum()), 3)
        entry['edge_above_0.5_visible'] = round(float(wts[m[vis, 0] > 0.5].sum()), 3)
    out['slots'][slot.name.replace('BAKE_', '')] = entry
    print(slot.name.ljust(40), entry, flush=True)
(HERE / 'Bake' / 'visibility_stats.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('A762_VISIBILITY', out['visible_area_share'])
