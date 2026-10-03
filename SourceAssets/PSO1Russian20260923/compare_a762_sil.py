"""Compare under-view silhouette holes: pristine A762 body vs mouthpatch vs cylpatch."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))

def sil_holes(blend):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    body = bpy.data.objects['PSO_ScopeBody']
    verts = [(body.matrix_world @ v.co) - DELTA for v in body.data.vertices]
    faces = [tuple(p.vertices) for p in body.data.polygons]
    tree = BVHTree.FromPolygons(verts, faces)
    target = DELTA + Vector((0.0, -0.04, 0.10))
    cam_loc = target + Vector((0.12, -0.05, -0.22))
    direction = (target - cam_loc).normalized()
    z_axis = -direction
    x_axis = z_axis.cross(Vector((0, 0, 1))); x_axis.normalize()
    y_axis = z_axis.cross(x_axis).normalized()
    half_w, half_h, steps = 0.22, 0.14, 60
    grid = [[False]*steps for _ in range(steps)]
    miss_pts = []
    for iy in range(steps):
        for ix in range(steps):
            u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
            dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
            h = tree.ray_cast(cam_loc, dir_w, 0.8)
            if h[0] is not None:
                grid[iy][ix] = True
            else:
                denom = dir_w.dot(direction)
                if abs(denom)>1e-8:
                    t = (target-cam_loc).dot(direction)/denom
                    p = cam_loc + dir_w*t - DELTA
                    if -0.06<p.x<0.06 and -0.08<p.y<0.02 and 0.05<p.z<0.13:
                        miss_pts.append(p)
    holes = 0
    hole_pts = []
    for iy in range(2, steps-2):
        for ix in range(2, steps-2):
            if grid[iy][ix]: continue
            n_hit = sum(1 for dy in range(-2,3) for dx in range(-2,3) if grid[iy+dy][ix+dx])
            if n_hit >= 12:
                holes += 1
                denom = 1
                u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
                dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
                t = (target-cam_loc).dot(direction)/dir_w.dot(direction)
                hole_pts.append(cam_loc + dir_w*t - DELTA)
    clusters = {}
    for p in hole_pts:
        key = (round(p.x/0.02)*0.02, round(p.y/0.02)*0.02, round(p.z/0.02)*0.02)
        clusters[key] = clusters.get(key, 0) + 1
    top = sorted(({'xyz':list(k),'n':n} for k,n in clusters.items()), key=lambda d:-d['n'])[:8]
    return {'holes': holes, 'roi_miss': len(miss_pts), 'clusters': top,
            'v': len(body.data.vertices), 'f': len(body.data.polygons)}

files = {
    'pristine': OUT/'PSO1_A762_Editable.before-tuck.blend',
    'mouthpatch': OUT/'PSO1_A762_mouthpatch_trial.blend',
    'cylpatch': OUT/'PSO1_A762_cylpatch_trial.blend',
}
rep = {k: sil_holes(v) for k,v in files.items()}
(OUT/'a762_sil_compare.json').write_text(json.dumps(rep, indent=2), encoding='utf-8')
print(json.dumps(rep, indent=2), flush=True)
