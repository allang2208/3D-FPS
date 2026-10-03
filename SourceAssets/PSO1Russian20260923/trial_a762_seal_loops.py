"""Isolate the mid-body rectangular hollow loop on PSO_ScopeBody and preview a cylinder seal."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_TUBE = 0.1024, 0.0203

src = O / 'PSO1_A762_Editable.blend'
bak = OUT / 'PSO1_A762_Editable.before-tuck.blend'
shutil.copy2(bak, src)

bpy.ops.wm.open_mainfile(filepath=str(src))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world.copy(); inv = mw.inverted()

bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

cands = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    a, b = e.verts
    mid = (a.co + b.co) * 0.5
    r = math.hypot(mid.x, mid.z - AXIS_Z)
    if -0.10 <= mid.y <= -0.02 and mid.z >= 0.06 and 0.012 <= r <= 0.055:
        cands.append(e)

used = set(); loops = []
for e0 in cands:
    if e0.index in used:
        continue
    loop = []; e = e0; v = e.verts[0]; guard = 0
    while e.index not in used and guard < 5000:
        used.add(e.index); loop.append(e); v = e.other_vert(v)
        nxt = None
        for e2 in v.link_edges:
            if e2 in cands and e2.index not in used:
                nxt = e2; break
        if nxt is None:
            break
        e = nxt; guard += 1
    if len(loop) >= 8:
        pts = []
        for ed in loop:
            for vv in ed.verts:
                pts.append(vv.co.copy())
        cx = sum(p.x for p in pts)/len(pts); cy = sum(p.y for p in pts)/len(pts); cz = sum(p.z for p in pts)/len(pts)
        loops.append({'edges': len(loop), 'center': [cx, cy, cz], 'edge_ids': [ed.index for ed in loop]})

loops.sort(key=lambda L: -L['edges'])
edge_by_i = {e.index: e for e in bm.edges}

def order_loop(edge_list):
    if not edge_list:
        return []
    rem = set(edge_list)
    e0 = edge_list[0]
    ordered_v = [e0.verts[0], e0.verts[1]]
    rem.remove(e0)
    while rem:
        end = ordered_v[-1]
        found = None
        for e in list(rem):
            if end in e.verts:
                found = e; break
        if found is None:
            break
        rem.remove(found)
        ordered_v.append(found.other_vert(end))
    if ordered_v and ordered_v[0] == ordered_v[-1]:
        ordered_v = ordered_v[:-1]
    return ordered_v

sealed = []
for L in loops[:8]:
    edges = [edge_by_i[i] for i in L['edge_ids'] if i in edge_by_i]
    verts = order_loop(edges)
    if len(verts) < 4:
        continue
    cx, cy, cz = L['center']
    cr = math.hypot(cx, cz - AXIS_Z)
    if cz > 0.128 or cr < 0.012:
        continue
    k = R_TUBE / cr
    center = bm.verts.new(Vector((cx * k, cy, AXIS_Z + (cz - AXIS_Z) * k)))
    faces_added = 0
    for i in range(len(verts)):
        a = verts[i]; b = verts[(i + 1) % len(verts)]
        try:
            bm.faces.new([a, b, center])
            faces_added += 1
        except ValueError:
            pass
    sealed.append({'center': [round(cx,4), round(cy,4), round(cz,4)], 'verts': len(verts),
                   'faces_added': faces_added, 'center_r': round(cr,4)})

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:
    p.use_smooth = True

for ob in scene.objects:
    if ob.type == 'MESH':
        keep = ob.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens')
        ob.hide_render = not keep; ob.hide_set(not keep)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1600; scene.render.resolution_y = 1000
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.01, -0.04, 0.09))
for name, off, hide_mount in [
    ('seal_tq', Vector((0.22, -0.22, 0.12)), False),
    ('seal_under', Vector((0.12, -0.05, -0.22)), False),
    ('seal_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('seal_side', Vector((0.30, 0.0, 0.03)), False),
]:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_mount
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_mount
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_seal_trial.blend'))
result = {'candidate_loops': [{'edges': L['edges'], 'center': [round(c,4) for c in L['center']]} for L in loops[:12]],
          'sealed': sealed}
(OUT / 'a762_seal_trial.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_SEAL_TRIAL', json.dumps(result), flush=True)
