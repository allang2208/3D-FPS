"""Seal A762 PSO body mount-cutout: cap tube mouth, then tuck flange (no holes_fill)."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_TUBE, R_IN = 0.1024, 0.0203, 0.0200

bak = OUT / 'PSO1_A762_Editable.before-tuck.blend'
work = OUT / 'PSO1_A762_mouthcap_work.blend'
shutil.copy2(bak, work)
bpy.ops.wm.open_mainfile(filepath=str(work))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world.copy(); inv = mw.inverted()
bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

def rad(co):
    return math.hypot(co.x, co.z - AXIS_Z)

def ang(co):
    return math.atan2(co.z - AXIS_Z, co.x)

# Mouth rim: boundary edge on the tube whose single face extends outward into the cutout.
mouth = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    a, b = e.verts
    if not (0.0188 <= rad(a.co) <= 0.0230 and 0.0188 <= rad(b.co) <= 0.0230):
        continue
    mid = (a.co + b.co) * 0.5
    if not (mid.x > -0.005 and -0.12 < mid.y < 0.06):
        continue
    f = e.link_faces[0]
    fc = f.calc_center_median()
    if rad(fc) < 0.0235:
        continue  # face stays on tube, not cutout wall
    if fc.z > 0.125:
        continue  # skip turret tops
    mouth.append(e)

used = set(); loops = []
for e0 in mouth:
    if e0.index in used:
        continue
    loop = []; e = e0; v = e.verts[0]
    while e.index not in used:
        used.add(e.index); loop.append(e); v = e.other_vert(v)
        nxt = None
        for e2 in v.link_edges:
            if e2 in mouth and e2.index not in used:
                nxt = e2; break
        if nxt is None:
            break
        e = nxt
    if len(loop) >= 4:
        loops.append(loop)

def order_verts(loop):
    rem = set(loop); e = loop[0]
    ordered = [e.verts[0], e.verts[1]]; rem.remove(e)
    while rem:
        end = ordered[-1]; found = None
        for e2 in list(rem):
            if end in e2.verts:
                found = e2; break
        if not found:
            break
        rem.remove(found); ordered.append(found.other_vert(end))
    if ordered and ordered[0] == ordered[-1]:
        ordered = ordered[:-1]
    return ordered

sealed = []
for loop in sorted(loops, key=len, reverse=True):
    verts = order_verts(loop)
    if len(verts) < 4:
        continue
    # Snap rim to exact tube
    for v in verts:
        dx, dz = v.co.x, v.co.z - AXIS_Z
        r = math.hypot(dx, dz)
        if r > 1e-9:
            k = R_TUBE / r
            v.co.x = dx * k; v.co.z = AXIS_Z + dz * k
    cy = sum(v.co.y for v in verts) / len(verts)
    angs = [ang(v.co) for v in verts]
    mean_ang = math.atan2(sum(math.sin(a) for a in angs)/len(angs),
                          sum(math.cos(a) for a in angs)/len(angs))
    # Span check: skip tiny / almost-full-circle optical rims
    # unwrap
    unwrapped = []
    for a in angs:
        d = a - mean_ang
        while d > math.pi: d -= 2*math.pi
        while d < -math.pi: d += 2*math.pi
        unwrapped.append(d)
    span = max(unwrapped) - min(unwrapped)
    if span < math.radians(25):
        continue
    if span > math.radians(300):
        continue  # full optical collar
    cx = R_TUBE * math.cos(mean_ang)
    cz = AXIS_Z + R_TUBE * math.sin(mean_ang)
    center = bm.verts.new(Vector((cx, cy, cz)))
    faces = 0
    for i in range(len(verts)):
        a = verts[i]; b = verts[(i+1) % len(verts)]
        try:
            f = bm.faces.new([a, b, center]); f.smooth = True; faces += 1
        except ValueError:
            pass
    sealed.append({'n': len(loop), 'faces': faces, 'span_deg': round(math.degrees(span),1),
                   'center': [round(cx,4), round(cy,4), round(cz,4)],
                   'ang_deg': round(math.degrees(mean_ang),1)})

# Tuck remaining cutout flange into tube (fins), excluding illuminator (x small & hanging)
seed = [v for v in bm.verts
        if rad(v.co) > 0.0215 and v.co.x > 0.012
        and -0.095 < v.co.y < 0.05 and v.co.z < 0.095]
patch = set(seed)
for v in seed:
    for e in v.link_edges:
        ov = e.other_vert(v)
        if ov.co.z < 0.100 and -0.10 < ov.co.y < 0.055 and ov.co.x > 0.005 and rad(ov.co) > 0.0195:
            patch.add(ov)
projected = 0
for v in patch:
    dx, dz = v.co.x, v.co.z - AXIS_Z
    r = math.hypot(dx, dz)
    if r > R_IN:
        k = R_IN / r
        v.co.x = dx * k; v.co.z = AXIS_Z + dz * k
        projected += 1

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bmesh.ops.dissolve_degenerate(bm, dist=5e-5, edges=bm.edges[:])
for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:
    p.use_smooth = True

# Silhouette hole recount (same under camera)
bv = [body.matrix_world @ v.co for v in body.data.vertices]
bf = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(bv, bf)
target = DELTA + Vector((0.0, -0.04, 0.10))
cam_loc = target + Vector((0.12, -0.05, -0.22))
direction = (target - cam_loc).normalized()
z_axis = -direction
x_axis = z_axis.cross(Vector((0, 0, 1))); x_axis.normalize()
y_axis = z_axis.cross(x_axis).normalized()
half_w, half_h = 0.22, 0.14
steps = 60
grid = [[False]*steps for _ in range(steps)]
hit_pt = [[None]*steps for _ in range(steps)]
for iy in range(steps):
    for ix in range(steps):
        u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
        dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
        h = tree.ray_cast(cam_loc, dir_w, 0.8)
        if h[0] is not None:
            grid[iy][ix] = True; hit_pt[iy][ix] = h[0]-DELTA
holes = 0
for iy in range(2, steps-2):
    for ix in range(2, steps-2):
        if grid[iy][ix]: continue
        n_hit = sum(1 for dy in range(-2,3) for dx in range(-2,3) if grid[iy+dy][ix+dx])
        if n_hit >= 12:
            holes += 1

report = {'mouth_edges': len(mouth), 'loops': len(loops), 'sealed': sealed,
          'projected_flange': projected, 'patch': len(patch),
          'silhouette_holes_after': holes}

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
    ('mouthcap_tq', Vector((0.22, -0.22, 0.12)), False),
    ('mouthcap_under', Vector((0.12, -0.05, -0.22)), False),
    ('mouthcap_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('mouthcap_bodyonly_tq', Vector((0.22, -0.22, 0.12)), True),
    ('mouthcap_side', Vector((0.30, 0.0, 0.03)), False),
]:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_mouthcap_trial.blend'))
(OUT / 'a762_mouthcap_trial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('A762_MOUTHCAP_TRIAL', json.dumps(report), flush=True)
