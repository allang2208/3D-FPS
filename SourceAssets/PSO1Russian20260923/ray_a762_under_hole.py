"""Unproject under-camera hole rays to locate the body opening in 3D."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
bv = [mw @ v.co for v in body.data.vertices]
bf = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(bv, bf)

target = DELTA + Vector((0.0, -0.04, 0.10))
cam_loc = target + Vector((0.12, -0.05, -0.22))
# Build camera rotation like Blender track-to
direction = (target - cam_loc).normalized()
# Approximate camera basis
z_axis = -direction  # camera looks along -Z
x_axis = z_axis.cross(Vector((0, 0, 1)))
if x_axis.length < 1e-6:
    x_axis = z_axis.cross(Vector((0, 1, 0)))
x_axis.normalize()
y_axis = z_axis.cross(x_axis).normalized()
# FOV from lens 70mm on 36mm sensor ~ 28.8 deg horizontal; use ~0.25 rad half-angle
half_w, half_h = 0.22, 0.14
misses = []
hits = []
steps = 40
for iy in range(steps):
    for ix in range(steps):
        u = (ix / (steps - 1)) * 2 - 1
        v = (iy / (steps - 1)) * 2 - 1
        # skip outer frame
        if abs(u) > 0.85 or abs(v) > 0.85:
            continue
        dir_w = (direction + x_axis * (u * half_w) + y_axis * (v * half_h)).normalized()
        h = tree.ray_cast(cam_loc, dir_w, 0.8)
        if h[0] is None:
            # record a point along the ray near expected body depth
            p = cam_loc + dir_w * 0.28 - DELTA
            if -0.12 < p.y < 0.08 and 0.05 < p.z < 0.16 and -0.05 < p.x < 0.05:
                misses.append({'u': round(u, 3), 'v': round(v, 3),
                               'x': round(p.x, 4), 'y': round(p.y, 4), 'z': round(p.z, 4)})
        else:
            p = h[0] - DELTA
            hits.append(p)

# Cluster misses
bins = {}
for m in misses:
    key = (round(m['x'] * 40) / 40, round(m['y'] * 40) / 40, round(m['z'] * 40) / 40)
    bins[key] = bins.get(key, 0) + 1
top = sorted(({'xyz': list(k), 'n': n} for k, n in bins.items()), key=lambda d: -d['n'])

# Also: for each miss, find nearest body point
near = []
for m in misses[:80]:
    pt = Vector((m['x'], m['y'], m['z'])) + DELTA
    loc, normal, index, dist = tree.find_nearest(pt)
    if loc is not None:
        q = loc - DELTA
        near.append({'miss': [m['x'], m['y'], m['z']], 'near': [round(q.x,4), round(q.y,4), round(q.z,4)],
                     'dist_mm': round(dist * 1000, 2)})

result = {'miss_count': len(misses), 'miss_bins': top[:20], 'near_sample': near[:15]}
(OUT / 'a762_under_hole_rays.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('UNDER_HOLE_RAYS', json.dumps(result), flush=True)
