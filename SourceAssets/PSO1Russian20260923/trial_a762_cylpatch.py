"""Seal A762 ScopeBody near-wall gaps with a cylinder-surface patch (no delete/holes_fill)."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_PATCH, R_IN = 0.1024, 0.02015, 0.0200

bak = OUT / 'PSO1_A762_Editable.before-tuck.blend'
work = OUT / 'PSO1_A762_cylpatch_work.blend'
shutil.copy2(bak, work)
bpy.ops.wm.open_mainfile(filepath=str(work))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world.copy(); inv = mw.inverted()

# --- detect near-wall gaps in body-local (delta-removed) space ---
verts_w = [(mw @ v.co) - DELTA for v in body.data.vertices]
faces_i = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(verts_w, faces_i)

ys = [round(i * 0.003 - 0.090, 4) for i in range(50)]       # -0.090 .. 0.057
angs_deg = list(range(-110, 55, 3))                          # mount/bottom sector
gap_mask = set()
for y in ys:
    for ad in angs_deg:
        a = math.radians(ad)
        ox, oz = math.cos(a), math.sin(a)
        start = Vector((1.7 * R_IN * ox, y, AXIS_Z + 1.7 * R_IN * oz))
        direction = Vector((-ox, 0.0, -oz))
        h = tree.ray_cast(start, direction, 2.4 * R_IN)
        is_gap = False
        if h[0] is None:
            is_gap = True
        else:
            hit = h[0]
            hx, hz = hit.x, hit.z - AXIS_Z
            hr = math.hypot(hx, hz)
            same = (hx * ox + hz * oz) > 0.0
            if (not same) or hr < 0.0170 or hr > 0.0285:
                is_gap = True
        if is_gap:
            gap_mask.add((y, ad))

# Dilate 1 cell so patch overlaps existing rim
dilated = set(gap_mask)
for y, ad in list(gap_mask):
    for dy in (-0.003, 0.0, 0.003):
        for da in (-3, 0, 3):
            dilated.add((round(y + dy, 4), ad + da))

# Restrict to main component band (avoid tiny foot tips / illuminator extremes)
dilated = {(y, ad) for (y, ad) in dilated
           if -0.055 <= y <= 0.050 and -105 <= ad <= 52}

# Build grid indices
ys_u = sorted({y for y, _ in dilated})
angs_u = sorted({ad for _, ad in dilated})
# Only keep y/ang that appear; create full rect spanning for continuity in each row
# Better: create verts for every (y,ang) in dilated, quads when 4 corners present

bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

vmap = {}
def vert_at(y, ad):
    key = (y, ad)
    if key in vmap:
        return vmap[key]
    a = math.radians(ad)
    co = Vector((R_PATCH * math.cos(a), y, AXIS_Z + R_PATCH * math.sin(a)))
    v = bm.verts.new(co)
    vmap[key] = v
    return v

for y, ad in dilated:
    vert_at(y, ad)

bm.verts.ensure_lookup_table()
quads = 0
skipped = 0
# neighbor steps matching our grid
ystep, astep = 0.003, 3
for y, ad in list(dilated):
    y2 = round(y + ystep, 4); ad2 = ad + astep
    corners = [(y, ad), (y, ad2), (y2, ad2), (y2, ad)]
    if not all(c in dilated for c in corners):
        skipped += 1
        continue
    vs = [vmap[c] for c in corners]
    try:
        f = bm.faces.new(vs)
        f.smooth = True
        quads += 1
    except ValueError:
        skipped += 1

# Mild flange tuck: only thin fins hanging below tube in the sealed window
seed = [v for v in bm.verts
        if math.hypot(v.co.x, v.co.z - AXIS_Z) > 0.022
        and v.co.x > 0.008
        and -0.060 < v.co.y < 0.050
        and v.co.z < 0.095]
# skip brand-new patch verts (exactly on R_PATCH)
patch_ids = {id(v) for v in vmap.values()}
seed = [v for v in seed if id(v) not in patch_ids]
patch_flange = set(seed)
for v in seed:
    for e in v.link_edges:
        ov = e.other_vert(v)
        if id(ov) in patch_ids:
            continue
        if ov.co.z < 0.100 and -0.065 < ov.co.y < 0.055 and ov.co.x > 0.004:
            if math.hypot(ov.co.x, ov.co.z - AXIS_Z) > 0.0195:
                patch_flange.add(ov)
projected = 0
for v in patch_flange:
    dx, dz = v.co.x, v.co.z - AXIS_Z
    r = math.hypot(dx, dz)
    if r > R_IN:
        k = R_IN / r
        v.co.x = dx * k; v.co.z = AXIS_Z + dz * k
        projected += 1

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
# Flip any new faces that point inward
axis = Vector((0.0, 0.0, AXIS_Z))
flipped = 0
for f in bm.faces:
    c = f.calc_center_median()
    radial = Vector((c.x, 0.0, c.z - AXIS_Z))
    if radial.length < 1e-9:
        continue
    if f.normal.dot(radial) < 0 and abs(math.hypot(c.x, c.z - AXIS_Z) - R_PATCH) < 0.0015:
        f.normal_flip(); flipped += 1

for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:
    p.use_smooth = True

# Re-measure gaps after patch
verts_w = [(body.matrix_world @ v.co) - DELTA for v in body.data.vertices]
faces_i = [tuple(p.vertices) for p in body.data.polygons]
tree2 = BVHTree.FromPolygons(verts_w, faces_i)
gaps_after = 0
roi_after = 0
for y in ys:
    for ad in angs_deg:
        a = math.radians(ad)
        ox, oz = math.cos(a), math.sin(a)
        start = Vector((1.7 * R_IN * ox, y, AXIS_Z + 1.7 * R_IN * oz))
        direction = Vector((-ox, 0.0, -oz))
        h = tree2.ray_cast(start, direction, 2.4 * R_IN)
        bad = False
        if h[0] is None:
            bad = True
        else:
            hit = h[0]; hx, hz = hit.x, hit.z - AXIS_Z
            hr = math.hypot(hx, hz)
            same = (hx * ox + hz * oz) > 0.0
            if (not same) or hr < 0.0170 or hr > 0.0285:
                bad = True
        if bad:
            gaps_after += 1
            if -0.055 <= y <= 0.050 and -105 <= ad <= 52:
                roi_after += 1

# Silhouette holes (under cam)
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
holes = 0
for iy in range(2, steps-2):
    for ix in range(2, steps-2):
        if grid[iy][ix]:
            continue
        n_hit = sum(1 for dy in range(-2,3) for dx in range(-2,3) if grid[iy+dy][ix+dx])
        if n_hit >= 12:
            holes += 1

report = {
    'gap_mask': len(gap_mask),
    'dilated': len(dilated),
    'new_verts': len(vmap),
    'quads': quads,
    'flipped': flipped,
    'projected_flange': projected,
    'gaps_after_total': gaps_after,
    'gaps_after_roi': roi_after,
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
    ('cylpatch_tq', Vector((0.22, -0.22, 0.12)), False),
    ('cylpatch_under', Vector((0.12, -0.05, -0.22)), False),
    ('cylpatch_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('cylpatch_bodyonly_tq', Vector((0.22, -0.22, 0.12)), True),
    ('cylpatch_side', Vector((0.30, 0.0, 0.03)), False),
]:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_cylpatch_trial.blend'))
(OUT / 'a762_cylpatch_trial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('A762_CYLPATCH', json.dumps(report), flush=True)
