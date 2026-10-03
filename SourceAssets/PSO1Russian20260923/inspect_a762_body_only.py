"""Render A762 PSO_ScopeBody alone and list its non-bore exterior openings."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
for ob in scene.objects:
    if ob.type == 'MESH':
        keep = ob.name == 'PSO_ScopeBody'
        ob.hide_render = not keep
        ob.hide_set(not keep)

mw = body.matrix_world
bv = [mw @ v.co for v in body.data.vertices]
bf = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(bv, bf)

bm = bmesh.new(); bm.from_mesh(body.data); bm.edges.ensure_lookup_table()
opens = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    mid = mw @ ((e.verts[0].co + e.verts[1].co) * 0.5)
    f = e.link_faces[0]
    n = (mw.to_3x3() @ f.normal).normalized()
    p = mid - DELTA
    r = math.hypot(p.x, p.z - AXIS_Z)
    if r < 0.023:
        continue  # optical bore
    # Covered by another body shell within 3mm outward?
    h = tree.ray_cast(mid + n * 0.0005, n, 0.003)
    if h[0] is not None and h[3] > 0.0003:
        continue
    opens.append({'x': round(p.x, 4), 'y': round(p.y, 4), 'z': round(p.z, 4), 'r': round(r, 4),
                  'nx': round(n.x, 2), 'ny': round(n.y, 2), 'nz': round(n.z, 2)})
bm.free()

bins = {}
for o in opens:
    key = (round(o['x']*20)/20, round(o['y']*20)/20, round(o['z']*20)/20)
    b = bins.setdefault(key, {'n': 0, 'rmax': 0})
    b['n'] += 1; b['rmax'] = max(b['rmax'], o['r'])
top = sorted(({'xyz': list(k), **v} for k, v in bins.items()), key=lambda d: -d['n'])

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'SINGLE'
sh.single_color = (0.65, 0.65, 0.67)
sh.show_backface_culling = True
sh.show_cavity = True; sh.cavity_type = 'BOTH'
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.0, -0.03, 0.10))
for name, off in {
    'bodyonly_tq': Vector((0.22, -0.22, 0.12)),
    'bodyonly_side': Vector((0.30, 0.0, 0.03)),
    'bodyonly_under': Vector((0.12, -0.05, -0.22)),
    'bodyonly_top': Vector((0.05, -0.05, 0.28)),
}.items():
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

result = {'exposed_nonbore_edges': len(opens), 'clusters': top[:25], 'sample': opens[:30]}
(OUT / 'a762_body_only_opens.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_BODY_ONLY', json.dumps({'n': len(opens), 'clusters': top[:15]}), flush=True)
