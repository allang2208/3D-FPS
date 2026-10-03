"""Cap the ScopeBody mount-cutout mouth on the tube cylinder (no holes_fill)."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_TUBE = 0.1024, 0.0203

bak = OUT / 'PSO1_A762_Editable.before-tuck.blend'
work = OUT / 'PSO1_A762_cap_work.blend'
shutil.copy2(bak, work)
bpy.ops.wm.open_mainfile(filepath=str(work))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world.copy(); inv = mw.inverted()
bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

def rad(co):
    return math.hypot(co.x, co.z - AXIS_Z)

# Mouth rim: boundary edges sitting on/near the tube on the mount side, mid body.
rim_edges = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    a, b = e.verts
    mid = (a.co + b.co) * 0.5
    ra, rb = rad(a.co), rad(b.co)
    if not (0.0185 <= ra <= 0.0235 and 0.0185 <= rb <= 0.0235):
        continue
    if not (mid.x > 0.0 and -0.10 < mid.y < 0.05 and mid.z < 0.12):
        continue
    # Prefer underside / mount-facing rim (not top of tube)
    ang = math.atan2(mid.z - AXIS_Z, mid.x)
    # mount side is roughly ang in [-100deg, +100deg] with +x; underside negative z relative axis
    rim_edges.append(e)

# Walk connected rim loops
used = set(); loops = []
for e0 in rim_edges:
    if e0.index in used:
        continue
    loop = []; e = e0; v = e.verts[0]
    while e.index not in used:
        used.add(e.index); loop.append(e); v = e.other_vert(v)
        nxt = None
        for e2 in v.link_edges:
            if e2 in rim_edges and e2.index not in used:
                nxt = e2; break
        if nxt is None:
            break
        e = nxt
    if len(loop) >= 6:
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

def ang_of(v):
    return math.atan2(v.co.z - AXIS_Z, v.co.x)

sealed = []
for loop in sorted(loops, key=len, reverse=True)[:6]:
    verts = order_verts(loop)
    if len(verts) < 6:
        continue
    # Project every rim vert exactly onto the tube (clean the rim)
    for v in verts:
        dx, dz = v.co.x, v.co.z - AXIS_Z
        r = math.hypot(dx, dz)
        if r > 1e-9:
            k = R_TUBE / r
            v.co.x = dx * k
            v.co.z = AXIS_Z + dz * k
    # Build a cylindrical fan: insert a center on the tube at mean angle/y
    cy = sum(v.co.y for v in verts) / len(verts)
    angs = [ang_of(v) for v in verts]
    # unwrap angles near mean
    mean_ang = math.atan2(sum(math.sin(a) for a in angs)/len(angs),
                          sum(math.cos(a) for a in angs)/len(angs))
    cx = R_TUBE * math.cos(mean_ang)
    cz = AXIS_Z + R_TUBE * math.sin(mean_ang)
    center = bm.verts.new(Vector((cx, cy, cz)))
    faces = 0
    for i in range(len(verts)):
        a = verts[i]; b = verts[(i + 1) % len(verts)]
        try:
            f = bm.faces.new([a, b, center])
            f.smooth = True
            faces += 1
        except ValueError:
            pass
    sealed.append({'edges': len(loop), 'verts': len(verts), 'faces': faces,
                   'center': [round(cx,4), round(cy,4), round(cz,4)],
                   'ang_deg': round(math.degrees(mean_ang),1)})

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
# dissolve degenerate that might appear on the rim
bmesh.ops.dissolve_degenerate(bm, dist=5e-5, edges=bm.edges[:])
for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:
    p.use_smooth = True

report = {'rim_edges': len(rim_edges), 'loops_found': len(loops), 'sealed': sealed}

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
    ('cap_tq', Vector((0.22, -0.22, 0.12)), False),
    ('cap_under', Vector((0.12, -0.05, -0.22)), False),
    ('cap_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('cap_bodyonly_tq', Vector((0.22, -0.22, 0.12)), True),
    ('cap_side', Vector((0.30, 0.0, 0.03)), False),
]:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_cap_trial.blend'))
(OUT / 'a762_cap_trial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('A762_CAP_TRIAL', json.dumps(report), flush=True)
