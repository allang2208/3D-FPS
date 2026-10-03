"""Unproject under-cam miss rays onto cylinder to get true gap (y,ang) map."""
import bpy, json, math
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R = 0.1024, 0.0200

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'PSO1_A762_Editable.before-tuck.blend'))
body = bpy.data.objects['PSO_ScopeBody']
verts = [(body.matrix_world @ v.co) - DELTA for v in body.data.vertices]
faces = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(verts, faces)

target = Vector((0.0, -0.04, 0.10))
cam_loc = target + Vector((0.12, -0.05, -0.22))
direction = (target - cam_loc).normalized()
z_axis = -direction
x_axis = z_axis.cross(Vector((0, 0, 1))); x_axis.normalize()
y_axis = z_axis.cross(x_axis).normalized()
half_w, half_h, steps = 0.22, 0.14, 90

# For miss rays: find t where ray is closest to optical axis (x=0,z=AXIS_Z line along y)
# Ray: P(t) = cam + t*dir. Axis line: (0, s, AXIS_Z).
# Closest: minimize |(cam_x + t*dx)^2 + (cam_z + t*dz - AXIS_Z)^2|
gap_hits = []  # points on cylinder where miss rays pierce R sphere-cylinder
for iy in range(steps):
    for ix in range(steps):
        u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
        dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
        h = tree.ray_cast(cam_loc, dir_w, 0.9)
        if h[0] is not None:
            continue
        # surrounded by hits?
        n_hit = 0
        for dy in range(-2,3):
            for dx in range(-2,3):
                if dy==0 and dx==0: continue
                i2, j2 = iy+dy, ix+dx
                if not (0<=i2<steps and 0<=j2<steps): continue
                u2 = (j2/(steps-1))*2-1; v2 = (i2/(steps-1))*2-1
                d2 = (direction + x_axis*(u2*half_w) + y_axis*(v2*half_h)).normalized()
                if tree.ray_cast(cam_loc, d2, 0.9)[0] is not None:
                    n_hit += 1
        if n_hit < 10:
            continue
        # intersect ray with cylinder x^2+(z-AXIS_Z)^2 = R^2
        # quadratic in t
        ox, oy, oz = cam_loc.x, cam_loc.y, cam_loc.z - AXIS_Z
        dx, dy, dz = dir_w.x, dir_w.y, dir_w.z
        A = dx*dx + dz*dz
        B = 2*(ox*dx + oz*dz)
        C = ox*ox + oz*oz - R*R
        disc = B*B - 4*A*C
        if A < 1e-12 or disc < 0:
            continue
        sd = math.sqrt(disc)
        ts = [(-B - sd)/(2*A), (-B + sd)/(2*A)]
        ts = [t for t in ts if t > 0.01]
        if not ts:
            continue
        t = min(ts)  # first cylinder intersection
        p = cam_loc + dir_w * t
        # verify still miss (no face before cylinder)
        h2 = tree.ray_cast(cam_loc, dir_w, t - 1e-4)
        if h2[0] is not None:
            continue
        a = math.degrees(math.atan2(p.z - AXIS_Z, p.x))
        gap_hits.append({'x': round(p.x,4), 'y': round(p.y,4), 'z': round(p.z,4),
                         'ang': round(a,1), 'r': round(math.hypot(p.x,p.z-AXIS_Z),4)})

bins = defaultdict(int)
for g in gap_hits:
    key = (round(g['y']/0.01)*0.01, round(g['ang']/10)*10)
    bins[key] += 1
clusters = [{'y': k[0], 'ang': k[1], 'n': n} for k,n in bins.items()]
clusters.sort(key=lambda d: -d['n'])

ys = [g['y'] for g in gap_hits]
angs = [g['ang'] for g in gap_hits]
report = {
    'gap_pierce_count': len(gap_hits),
    'y_extent': [min(ys), max(ys)] if ys else None,
    'ang_extent': [min(angs), max(angs)] if angs else None,
    'clusters_top': clusters[:20],
    'samples': gap_hits[:30],
}
(OUT/'a762_gap_on_cylinder.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('GAP_CYL', json.dumps({
    'n': len(gap_hits),
    'y': report['y_extent'],
    'ang': report['ang_extent'],
    'top': clusters[:8],
}), flush=True)
