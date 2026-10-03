"""Seal A762 body under-view cylinder gap (bottom/mount sector). No flange tuck."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_IN, R_PATCH = 0.1024, 0.0200, 0.02025

bak = OUT / 'PSO1_A762_Editable.before-tuck.blend'
work = OUT / 'PSO1_A762_bottomseal_work.blend'
shutil.copy2(bak, work)
bpy.ops.wm.open_mainfile(filepath=str(work))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world.copy(); inv = mw.inverted()

verts_w = [(mw @ v.co) - DELTA for v in body.data.vertices]
faces_i = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(verts_w, faces_i)

ys = [round(-0.095 + i * 0.0025, 4) for i in range(int(0.125/0.0025)+1)]  # -0.095 .. 0.030
angs = list(range(-155, 30, 3))

def is_gap(y, adeg):
    a = math.radians(adeg)
    ox, oz = math.cos(a), math.sin(a)
    start = Vector((1.75 * R_IN * ox, y, AXIS_Z + 1.75 * R_IN * oz))
    h = tree.ray_cast(start, Vector((-ox, 0.0, -oz)), 0.055)
    if h[0] is None:
        return True
    hit = h[0]; hx, hz = hit.x, hit.z - AXIS_Z
    hr = math.hypot(hx, hz)
    same = (hx * ox + hz * oz) > 0.0
    return (not same) or hr < 0.0170 or hr > 0.0288

mask = {(y, ad) for y in ys for ad in angs if is_gap(y, ad)}
dil = set(mask)
for y, ad in list(mask):
    for dy in (-0.0025, 0, 0.0025):
        for da in (-3, 0, 3):
            yy = round(y + dy, 4)
            if ys[0] <= yy <= ys[-1] and angs[0] <= ad + da <= angs[-1]:
                dil.add((yy, ad + da))

bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

vmap = {}
def V(y, ad):
    key = (y, ad)
    if key in vmap:
        return vmap[key]
    a = math.radians(ad)
    v = bm.verts.new(Vector((R_PATCH * math.cos(a), y, AXIS_Z + R_PATCH * math.sin(a))))
    vmap[key] = v
    return v

for y, ad in dil:
    V(y, ad)

ystep, astep = 0.0025, 3
quads = 0
for y, ad in list(dil):
    corners = [(y, ad), (y, ad + astep), (round(y + ystep, 4), ad + astep), (round(y + ystep, 4), ad)]
    if not all(c in dil for c in corners):
        continue
    try:
        f = bm.faces.new([V(*c) for c in corners])
        f.smooth = True
        quads += 1
    except ValueError:
        pass

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
flipped = 0
for f in bm.faces:
    c = f.calc_center_median()
    radial = Vector((c.x, 0.0, c.z - AXIS_Z))
    if radial.length > 1e-8 and abs(math.hypot(c.x, c.z - AXIS_Z) - R_PATCH) < 0.0015:
        if f.normal.dot(radial) < 0:
            f.normal_flip(); flipped += 1

for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:
    p.use_smooth = True

# verify gap-on-cylinder under cam
verts2 = [(body.matrix_world @ v.co) - DELTA for v in body.data.vertices]
faces2 = [tuple(p.vertices) for p in body.data.polygons]
tree2 = BVHTree.FromPolygons(verts2, faces2)
target = Vector((0.0, -0.04, 0.10))
cam_loc = target + Vector((0.12, -0.05, -0.22))
direction = (target - cam_loc).normalized()
z_axis = -direction
x_axis = z_axis.cross(Vector((0, 0, 1))); x_axis.normalize()
y_axis = z_axis.cross(x_axis).normalized()
half_w, half_h, steps = 0.22, 0.14, 90
pierce = 0
for iy in range(steps):
    for ix in range(steps):
        u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
        dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
        if tree2.ray_cast(cam_loc, dir_w, 0.9)[0] is not None:
            continue
        n_hit = sum(1 for dy in range(-2,3) for dx in range(-2,3)
                    if not (dy==0 and dx==0)
                    and 0<=iy+dy<steps and 0<=ix+dx<steps
                    and tree2.ray_cast(cam_loc, (direction + x_axis*(((ix+dx)/(steps-1))*2-1)*half_w + y_axis*(((iy+dy)/(steps-1))*2-1)*half_h).normalized(), 0.9)[0] is not None)
        if n_hit < 10:
            continue
        ox, oz = cam_loc.x, cam_loc.z - AXIS_Z
        dx, dz = dir_w.x, dir_w.z
        A = dx*dx + dz*dz; B = 2*(ox*dx + oz*dz); C = ox*ox + oz*oz - R_IN*R_IN
        disc = B*B - 4*A*C
        if A < 1e-12 or disc < 0:
            continue
        sd = math.sqrt(disc)
        ts = [t for t in [(-B-sd)/(2*A), (-B+sd)/(2*A)] if t > 0.01]
        if not ts:
            continue
        t = min(ts)
        if tree2.ray_cast(cam_loc, dir_w, t - 1e-4)[0] is None:
            pierce += 1

# nearwall gaps remaining in ROI (against sealed mesh)
remain = 0
for y in ys:
    for ad in angs:
        a = math.radians(ad); ox, oz = math.cos(a), math.sin(a)
        start = Vector((1.75*R_IN*ox, y, AXIS_Z + 1.75*R_IN*oz))
        h = tree2.ray_cast(start, Vector((-ox,0,-oz)), 0.055)
        bad = h[0] is None
        if not bad:
            hit=h[0]; hx,hz=hit.x,hit.z-AXIS_Z; hr=math.hypot(hx,hz)
            same=(hx*ox+hz*oz)>0
            bad=(not same) or hr<0.017 or hr>0.0288
        if bad:
            remain += 1

report = {
    'mask': len(mask), 'dilated': len(dil), 'verts': len(vmap), 'quads': quads,
    'flipped': flipped, 'under_pierce_after': pierce, 'nearwall_remain': remain,
    'mesh': {'v': len(body.data.vertices), 'f': len(body.data.polygons)},
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
target_r = DELTA + Vector((0.01, -0.04, 0.09))
for name, off, hide_m in [
    ('bottomseal_tq', Vector((0.22, -0.22, 0.12)), False),
    ('bottomseal_under', Vector((0.12, -0.05, -0.22)), False),
    ('bottomseal_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('bottomseal_bodyonly_tq', Vector((0.22, -0.22, 0.12)), True),
    ('bottomseal_side', Vector((0.30, 0.0, 0.03)), False),
]:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target_r + off
    cam.rotation_euler = (target_r - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_bottomseal_trial.blend'))
(OUT / 'a762_bottomseal_trial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BOTTOMSEAL', json.dumps(report), flush=True)
