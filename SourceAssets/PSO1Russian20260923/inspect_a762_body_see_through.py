"""Locate see-through openings on A762 PSO body (not gun adapters)."""
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

for ob in scene.objects:
    if ob.type != 'MESH':
        continue
    keep = ob.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens')
    ob.hide_render = not keep
    ob.hide_set(not keep)

body = bpy.data.objects['PSO_ScopeBody']
mount = bpy.data.objects['PSO_ScopeMount']
lens = bpy.data.objects['PSO_ScopeLens']


def world_parts(ob, skip_optical_glass=False):
    mw = ob.matrix_world
    verts = [mw @ v.co for v in ob.data.vertices]
    faces = []
    for p in ob.data.polygons:
        mat = ob.data.materials[p.material_index] if ob.data.materials else None
        name = mat.name if mat else ''
        if skip_optical_glass and 'OpticalGlass' in name:
            continue
        faces.append(tuple(p.vertices))
    return verts, faces


bv = []; bf = []
for ob, skip in ((body, False), (mount, False), (lens, True)):
    v, f = world_parts(ob, skip_optical_glass=skip)
    base = len(bv)
    bv.extend(v)
    bf.extend(tuple(base + i for i in face) for face in f)
opaque = BVHTree.FromPolygons(bv, bf)

exposes = []
ys = [i * 0.01 for i in range(-18, 14)]
angles = 48
for y in ys:
    for i in range(angles):
        ang = 2 * math.pi * i / angles
        direction = Vector((-math.cos(ang), 0.0, -math.sin(ang)))
        start = Vector((math.cos(ang) * 0.04, y, AXIS_Z + math.sin(ang) * 0.04)) + DELTA
        hit = opaque.ray_cast(start, direction, 0.045)
        if hit[0] is None:
            exposes.append({'y': round(y, 3), 'ang': round(ang * 180 / math.pi, 1)})

bm = bmesh.new(); bm.from_mesh(body.data); bm.edges.ensure_lookup_table()
mw = body.matrix_world
uncovered = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    mid = mw @ ((e.verts[0].co + e.verts[1].co) * 0.5)
    f = e.link_faces[0]
    n = (mw.to_3x3() @ f.normal).normalized()
    h = opaque.ray_cast(mid + n * 0.0005, n, 0.004)
    if h[0] is None:
        h2 = opaque.ray_cast(mid - n * 0.0002, n, 0.006)
        if h2[0] is None:
            p = mid - DELTA
            uncovered.append([round(p.x, 4), round(p.y, 4), round(p.z, 4)])
bm.free()

bins = {}
for x, y, z in uncovered:
    key = (round(x * 20) / 20, round(y * 20) / 20, round(z * 20) / 20)
    bins[key] = bins.get(key, 0) + 1
top_bins = sorted(({'xyz': list(k), 'n': n} for k, n in bins.items()), key=lambda d: -d['n'])[:25]

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True
sh.show_cavity = True; sh.cavity_type = 'BOTH'
cam = bpy.data.objects.new('BodyCam', bpy.data.cameras.new('BodyCam'))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.lens = 65
target = DELTA + Vector((0.0, -0.02, 0.10))
views = {
    'body_side': Vector((0.32, 0.0, 0.02)),
    'body_three_quarter': Vector((0.24, -0.24, 0.14)),
    'body_front': Vector((0.02, -0.35, 0.05)),
    'body_under': Vector((0.15, -0.05, -0.25)),
}
for name, off in views.items():
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

result = {
    'outside_to_axis_misses': len(exposes),
    'expose_sample': exposes[:40],
    'uncovered_boundary_edge_mids': len(uncovered),
    'uncovered_bins': top_bins,
}
(OUT / 'a762_body_see_through.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_BODY_SEE_THROUGH', json.dumps(result), flush=True)
