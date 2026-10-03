"""Seal the under-view rectangular hole by filling the 3D ring of surrounding hit points."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bak = OUT / 'PSO1_A762_Editable.before-tuck.blend'
work = OUT / 'PSO1_A762_ringfill_work.blend'
shutil.copy2(bak, work)
bpy.ops.wm.open_mainfile(filepath=str(work))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world.copy(); inv = mw.inverted()

verts = [(mw @ v.co) - DELTA for v in body.data.vertices]
faces = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(verts, faces)

target = Vector((0.0, -0.04, 0.10))
cam_loc = target + Vector((0.12, -0.05, -0.22))
direction = (target - cam_loc).normalized()
z_axis = -direction
x_axis = z_axis.cross(Vector((0, 0, 1))); x_axis.normalize()
y_axis = z_axis.cross(x_axis).normalized()
half_w, half_h, steps = 0.18, 0.12, 100

hit_pt = [[None]*steps for _ in range(steps)]
hit_ok = [[False]*steps for _ in range(steps)]
for iy in range(steps):
    for ix in range(steps):
        u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
        dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
        h = tree.ray_cast(cam_loc, dir_w, 0.9)
        if h[0] is not None:
            hit_ok[iy][ix] = True
            hit_pt[iy][ix] = h[0].copy()

# hole pixels: miss surrounded by hits
holes = []
for iy in range(3, steps-3):
    for ix in range(3, steps-3):
        if hit_ok[iy][ix]:
            continue
        n_hit = sum(1 for dy in range(-3,4) for dx in range(-3,4) if hit_ok[iy+dy][ix+dx])
        if n_hit >= 20:
            holes.append((iy, ix))

# Collect boundary hit points around each hole cluster (unique-ish)
ring = []
seen = set()
for iy, ix in holes:
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            jy, jx = iy + dy, ix + dx
            if not (0 <= jy < steps and 0 <= jx < steps):
                continue
            if not hit_ok[jy][jx]:
                continue
            # only if adjacent to a miss
            adj_miss = False
            for ady in (-1, 0, 1):
                for adx in (-1, 0, 1):
                    ky, kx = jy + ady, jx + adx
                    if 0 <= ky < steps and 0 <= kx < steps and not hit_ok[ky][kx]:
                        adj_miss = True
                        break
                if adj_miss:
                    break
            if not adj_miss:
                continue
            p = hit_pt[jy][jx]
            key = (round(p.x, 4), round(p.y, 4), round(p.z, 4))
            if key in seen:
                continue
            seen.add(key)
            ring.append(p.copy())

# Filter ring to ROI near body underside hole (exclude far hits)
ring = [p for p in ring
        if -0.07 < p.x < 0.07 and -0.12 < p.y < 0.05 and 0.04 < p.z < 0.14]

# Cluster ring points by proximity into connected opening(s)
# Use simple: take the largest spatial cluster via greedy
def cluster_points(pts, dist=0.012):
    if not pts:
        return []
    remaining = list(pts)
    clusters = []
    while remaining:
        seed = remaining.pop()
        comp = [seed]
        changed = True
        while changed:
            changed = False
            for p in list(remaining):
                if any((p-q).length < dist for q in comp):
                    remaining.remove(p); comp.append(p); changed = True
        clusters.append(comp)
    clusters.sort(key=len, reverse=True)
    return clusters

clusters = cluster_points(ring, 0.015)

bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

filled = []
for ci, pts in enumerate(clusters[:3]):
    if len(pts) < 8:
        continue
    # Order points around centroid in a plane (PCA-ish: use cam-facing plane)
    # Project onto plane with normal ~ direction (from under cam)
    n = direction.copy(); n.normalize()
    # build orthonormal basis on plane
    t1 = n.cross(Vector((0,1,0)))
    if t1.length < 1e-6:
        t1 = n.cross(Vector((1,0,0)))
    t1.normalize(); t2 = n.cross(t1).normalized()
    c = sum(pts, Vector((0,0,0))) / len(pts)
    ordered = sorted(pts, key=lambda p: math.atan2((p-c).dot(t2), (p-c).dot(t1)))
    # Deduplicate consecutive near-equals
    clean = [ordered[0]]
    for p in ordered[1:]:
        if (p - clean[-1]).length > 0.0015:
            clean.append(p)
    if len(clean) >= 3 and (clean[0] - clean[-1]).length < 0.0015:
        clean = clean[:-1]
    if len(clean) < 6:
        continue
    # Create verts + fan fill from centroid (centroid pushed slightly outward along radial or along -n toward camera)
    # Place fill slightly toward camera so it covers the opening from outside
    center_co = c - n * 0.0005
    # If center is inside tube (small r), push to housing underside instead
    cr = math.hypot(center_co.x, center_co.z - AXIS_Z)
    if cr < 0.018:
        # push outward in xz
        if cr > 1e-6:
            k = 0.022 / cr
            center_co = Vector((center_co.x * k, center_co.y, AXIS_Z + (center_co.z - AXIS_Z) * k))
        else:
            center_co = Vector((0.0, center_co.y, AXIS_Z - 0.022))

    cv = bm.verts.new(center_co)
    bverts = [bm.verts.new(p) for p in clean]
    faces_n = 0
    for i in range(len(bverts)):
        a = bverts[i]; b = bverts[(i+1)%len(bverts)]
        try:
            f = bm.faces.new([a, b, cv])
            f.smooth = True
            faces_n += 1
        except ValueError:
            pass
    # Flip faces toward camera if needed
    for f in list(bm.faces)[-faces_n:]:
        if f.normal.dot(n) > 0:  # n points away from cam (from cam toward target); want normal toward cam = -n
            f.normal_flip()
    filled.append({'cluster': ci, 'ring': len(clean), 'faces': faces_n,
                   'center': [round(center_co.x,4), round(center_co.y,4), round(center_co.z,4)],
                   'cr': round(math.hypot(center_co.x, center_co.z-AXIS_Z),4)})

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:
    p.use_smooth = True

# recount hole pixels
verts2 = [(body.matrix_world @ v.co) - DELTA for v in body.data.vertices]
faces2 = [tuple(p.vertices) for p in body.data.polygons]
tree2 = BVHTree.FromPolygons(verts2, faces2)
holes_after = 0
for iy in range(3, steps-3):
    for ix in range(3, steps-3):
        u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
        dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
        if tree2.ray_cast(cam_loc, dir_w, 0.9)[0] is not None:
            continue
        n_hit = sum(1 for dy in range(-3,4) for dx in range(-3,4)
                    if tree2.ray_cast(cam_loc, (direction + x_axis*(((ix+dx)/(steps-1))*2-1)*half_w + y_axis*(((iy+dy)/(steps-1))*2-1)*half_h).normalized(), 0.9)[0] is not None)
        if n_hit >= 20:
            holes_after += 1

report = {
    'holes_before_pixels': len(holes),
    'ring_points': len(ring),
    'clusters': [len(c) for c in clusters[:5]],
    'filled': filled,
    'holes_after_pixels': holes_after,
}

for ob in scene.objects:
    if ob.type == 'MESH':
        keep = ob.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens')
        ob.hide_render = not keep; ob.hide_set(not keep)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1700; scene.render.resolution_y = 1100
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
for o in list(scene.objects):
    if o.type=='CAMERA':
        bpy.data.objects.remove(o, do_unlink=True)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target_r = DELTA + Vector((0.01, -0.04, 0.09))
for name, off, hide_m in [
    ('ringfill_under', Vector((0.12, -0.05, -0.22)), False),
    ('ringfill_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('ringfill_bodyonly_tq', Vector((0.22, -0.22, 0.12)), True),
    ('ringfill_side', Vector((0.30, 0.0, 0.03)), False),
]:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target_r + off
    cam.rotation_euler = (target_r - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_ringfill_trial.blend'))
(OUT / 'a762_ringfill_trial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RINGFILL', json.dumps(report), flush=True)
