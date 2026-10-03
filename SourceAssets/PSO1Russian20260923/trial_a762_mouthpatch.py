"""Build precise tube-mouth patch between cutout wall planes; no flange tuck."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_PATCH = 0.1024, 0.0201

bak = OUT / 'PSO1_A762_Editable.before-tuck.blend'
work = OUT / 'PSO1_A762_mouthpatch_work.blend'
shutil.copy2(bak, work)
bpy.ops.wm.open_mainfile(filepath=str(work))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mount = bpy.data.objects.get('PSO_ScopeMount')
mw = body.matrix_world.copy(); inv = mw.inverted()

# Mount bbox in body-local
mount_info = None
if mount:
    mverts = [(mw.inverted() @ (mount.matrix_world @ v.co)) for v in mount.data.vertices]
    # actually want same DELTA space
    mverts = [(mount.matrix_world @ v.co) - DELTA for v in mount.data.vertices]
    mount_info = {
        'x': [round(min(v.x for v in mverts),4), round(max(v.x for v in mverts),4)],
        'y': [round(min(v.y for v in mverts),4), round(max(v.y for v in mverts),4)],
        'z': [round(min(v.z for v in mverts),4), round(max(v.z for v in mverts),4)],
    }

bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

def rad(co):
    return math.hypot(co.x, co.z - AXIS_Z)
def ang(co):
    return math.atan2(co.z - AXIS_Z, co.x)

# Tube-rim boundary verts in cutout window
rim = []
for v in bm.verts:
    if not any(e.is_boundary for e in v.link_edges):
        continue
    if not (0.0194 <= rad(v.co) <= 0.0218):
        continue
    if v.co.x < 0.0:
        continue
    if not (-0.070 <= v.co.y <= 0.010):
        continue
    if v.co.z > 0.125:
        continue
    rim.append(v)

angs = [ang(v.co) for v in rim]
ys = [v.co.y for v in rim]
ang_min, ang_max = min(angs), max(angs)
y_min, y_max = min(ys), max(ys)
# pad
ang_min -= math.radians(8); ang_max += math.radians(8)
y_min -= 0.004; y_max += 0.004

# Also include wallish y planes known from prior: expand to cover both walls
y_min = min(y_min, -0.048); y_max = max(y_max, -0.012)

# Dense grid patch
ny = max(4, int((y_max - y_min) / 0.0025) + 1)
na = max(6, int((ang_max - ang_min) / math.radians(3)) + 1)
ys_g = [y_min + (y_max - y_min) * i / (ny - 1) for i in range(ny)]
angs_g = [ang_min + (ang_max - ang_min) * i / (na - 1) for i in range(na)]

# Only add patch cells that are currently open (near-wall gap test)
verts_w = [v.co.copy() for v in bm.verts]
faces_i = [tuple(v.index for v in f.verts) for f in bm.faces]
# need indices after ensure
bm.verts.ensure_lookup_table()
verts_w = [v.co.copy() for v in bm.verts]
faces_i = [tuple(v.index for v in f.verts) for f in bm.faces]
tree = BVHTree.FromPolygons(verts_w, faces_i)

def is_gap(y, a):
    ox, oz = math.cos(a), math.sin(a)
    start = Vector((1.7 * 0.020 * ox, y, AXIS_Z + 1.7 * 0.020 * oz))
    direction = Vector((-ox, 0.0, -oz))
    h = tree.ray_cast(start, direction, 0.05)
    if h[0] is None:
        return True
    hit = h[0]; hx, hz = hit.x, hit.z - AXIS_Z
    hr = math.hypot(hx, hz)
    same = (hx * ox + hz * oz) > 0.0
    return (not same) or hr < 0.0170 or hr > 0.0285

cell_ok = {}
for iy, y in enumerate(ys_g):
    for ia, a in enumerate(angs_g):
        cell_ok[(iy, ia)] = is_gap(y, a)

# dilate
dil = set()
for (iy, ia), ok in cell_ok.items():
    if not ok:
        continue
    for dy in (-1, 0, 1):
        for da in (-1, 0, 1):
            n = (iy + dy, ia + da)
            if n[0] < 0 or n[0] >= ny or n[1] < 0 or n[1] >= na:
                continue
            dil.add(n)

vmap = {}
def V(iy, ia):
    key = (iy, ia)
    if key in vmap:
        return vmap[key]
    y = ys_g[iy]; a = angs_g[ia]
    v = bm.verts.new(Vector((R_PATCH * math.cos(a), y, AXIS_Z + R_PATCH * math.sin(a))))
    vmap[key] = v
    return v

for iy, ia in dil:
    V(iy, ia)

quads = 0
for iy in range(ny - 1):
    for ia in range(na - 1):
        corners = [(iy, ia), (iy, ia + 1), (iy + 1, ia + 1), (iy + 1, ia)]
        if not all(c in dil for c in corners):
            continue
        try:
            f = bm.faces.new([V(*c) for c in corners])
            f.smooth = True
            quads += 1
        except ValueError:
            pass

# outward normals
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
flipped = 0
for f in bm.faces:
    c = f.calc_center_median()
    radial = Vector((c.x, 0.0, c.z - AXIS_Z))
    if radial.length > 1e-8 and abs(rad(c) - R_PATCH) < 0.0012:
        if f.normal.dot(radial) < 0:
            f.normal_flip(); flipped += 1

for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:
    p.use_smooth = True

# measure silhouette holes
verts2 = [(body.matrix_world @ v.co) - DELTA for v in body.data.vertices]
faces2 = [tuple(p.vertices) for p in body.data.polygons]
tree2 = BVHTree.FromPolygons(verts2, faces2)
target = DELTA + Vector((0.0, -0.04, 0.10))
cam_loc = target + Vector((0.12, -0.05, -0.22))
direction = (target - cam_loc).normalized()
z_axis = -direction
x_axis = z_axis.cross(Vector((0, 0, 1))); x_axis.normalize()
y_axis = z_axis.cross(x_axis).normalized()
half_w, half_h, steps = 0.22, 0.14, 60
grid = [[False]*steps for _ in range(steps)]
for iy in range(steps):
    for ix in range(steps):
        u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
        dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
        h = tree2.ray_cast(cam_loc, dir_w, 0.8)
        if h[0] is not None:
            grid[iy][ix] = True
holes = sum(1 for iy in range(2, steps-2) for ix in range(2, steps-2)
            if (not grid[iy][ix]) and sum(1 for dy in range(-2,3) for dx in range(-2,3) if grid[iy+dy][ix+dx]) >= 12)

# gap recount in window
gaps = 0
for y in ys_g:
    for a in angs_g:
        ox, oz = math.cos(a), math.sin(a)
        start = Vector((1.7*0.020*ox, y, AXIS_Z + 1.7*0.020*oz))
        h = tree2.ray_cast(start, Vector((-ox,0,-oz)), 0.05)
        bad = h[0] is None
        if not bad:
            hit=h[0]; hx,hz=hit.x,hit.z-AXIS_Z; hr=math.hypot(hx,hz)
            same=(hx*ox+hz*oz)>0
            bad = (not same) or hr<0.017 or hr>0.0285
        if bad: gaps += 1

report = {
    'mount_bbox': mount_info,
    'rim_verts': len(rim),
    'ang_deg': [round(math.degrees(ang_min),1), round(math.degrees(ang_max),1)],
    'y': [round(y_min,4), round(y_max,4)],
    'grid': [ny, na],
    'dil_cells': len(dil),
    'quads': quads,
    'flipped': flipped,
    'gaps_in_window': gaps,
    'silhouette_holes': holes,
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
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.01, -0.04, 0.09))
for name, off, hide_m in [
    ('mouthpatch_tq', Vector((0.22, -0.22, 0.12)), False),
    ('mouthpatch_under', Vector((0.12, -0.05, -0.22)), False),
    ('mouthpatch_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('mouthpatch_bodyonly_tq', Vector((0.22, -0.22, 0.12)), True),
    ('mouthpatch_side', Vector((0.30, 0.0, 0.03)), False),
]:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_mouthpatch_trial.blend'))
(OUT / 'a762_mouthpatch_trial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MOUTHPATCH', json.dumps(report), flush=True)
