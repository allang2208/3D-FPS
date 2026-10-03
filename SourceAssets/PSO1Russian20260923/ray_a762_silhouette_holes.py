"""Find silhouette-interior holes via under-camera ray grid."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
tree = BVHTree.FromPolygons([mw @ v.co for v in body.data.vertices],
                            [tuple(p.vertices) for p in body.data.polygons])

target = DELTA + Vector((0.0, -0.04, 0.10))
cam_loc = target + Vector((0.12, -0.05, -0.22))
direction = (target - cam_loc).normalized()
z_axis = -direction
x_axis = z_axis.cross(Vector((0, 0, 1)))
if x_axis.length < 1e-6:
    x_axis = z_axis.cross(Vector((0, 1, 0)))
x_axis.normalize()
y_axis = z_axis.cross(x_axis).normalized()
half_w, half_h = 0.22, 0.14
steps = 60
grid = [[False]*steps for _ in range(steps)]
hit_pt = [[None]*steps for _ in range(steps)]
for iy in range(steps):
    for ix in range(steps):
        u = (ix / (steps - 1)) * 2 - 1
        v = (iy / (steps - 1)) * 2 - 1
        dir_w = (direction + x_axis * (u * half_w) + y_axis * (v * half_h)).normalized()
        h = tree.ray_cast(cam_loc, dir_w, 0.8)
        if h[0] is not None:
            grid[iy][ix] = True
            hit_pt[iy][ix] = h[0] - DELTA

holes = []
for iy in range(2, steps-2):
    for ix in range(2, steps-2):
        if grid[iy][ix]:
            continue
        # count neighboring hits in 5x5
        n_hit = 0
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if grid[iy+dy][ix+dx]:
                    n_hit += 1
        if n_hit >= 12:  # surrounded by body
            # estimate 3D by averaging neighbor hits
            pts = []
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    p = hit_pt[iy+dy][ix+dx]
                    if p is not None:
                        pts.append(p)
            if not pts:
                continue
            c = sum(pts, Vector()) / len(pts)
            holes.append({'ix': ix, 'iy': iy, 'n_hit': n_hit,
                          'x': round(c.x, 4), 'y': round(c.y, 4), 'z': round(c.z, 4),
                          'r': round(math.hypot(c.x, c.z - AXIS_Z), 4)})

bins = {}
for h in holes:
    key = (round(h['x']*25)/25, round(h['y']*25)/25, round(h['z']*25)/25)
    b = bins.setdefault(key, {'n': 0})
    b['n'] += 1
top = sorted(({'xyz': list(k), **v} for k, v in bins.items()), key=lambda d: -d['n'])
result = {'silhouette_holes': len(holes), 'clusters': top[:15], 'sample': holes[::max(1,len(holes)//20)][:20]}
(OUT/'a762_silhouette_holes.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('SILHOUETTE_HOLES', json.dumps(result), flush=True)
