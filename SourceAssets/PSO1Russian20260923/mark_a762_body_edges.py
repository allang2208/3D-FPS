"""Overlay all non-bore body boundary edges as red tubes and render body-only."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world

bm = bmesh.new(); bm.from_mesh(body.data); bm.edges.ensure_lookup_table()
segs = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    a = mw @ e.verts[0].co; b = mw @ e.verts[1].co
    mid = (a + b) * 0.5 - DELTA
    r = math.hypot(mid.x, mid.z - AXIS_Z)
    if r < 0.023:
        continue
    segs.append((a, b))
bm.free()

# Build a mesh of thin boxes along segments
verts = []; faces = []
rad = 0.00035
for a, b in segs:
    d = b - a
    if d.length < 1e-9:
        continue
    d.normalize()
    # arbitrary perpendiculars
    ax = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
    p = d.cross(ax).normalized() * rad
    q = d.cross(p).normalized() * rad
    base = len(verts)
    for s, pt in ((-1, a), (1, b)):
        for sp, sq in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append(tuple(pt + sp * p + sq * q))
    # side faces between a-ring (0..3) and b-ring (4..7)
    for i in range(4):
        j = (i + 1) % 4
        faces.append((base+i, base+j, base+4+j, base+4+i))

me = bpy.data.meshes.new('EDGE_MARK')
me.from_pydata(verts, [], faces); me.update()
mark = bpy.data.objects.new('EDGE_MARK', me)
scene.collection.objects.link(mark)
mat = bpy.data.materials.new('RED')
mat.use_nodes = True
bs = mat.node_tree.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value = (1, 0.05, 0.02, 1)
bs.inputs['Emission Color'].default_value = (1, 0.15, 0.05, 1)
bs.inputs['Emission Strength'].default_value = 8
mark.data.materials.append(mat)

for ob in scene.objects:
    if ob.type == 'MESH':
        keep = ob.name in ('PSO_ScopeBody', 'EDGE_MARK')
        ob.hide_render = not keep; ob.hide_set(not keep)

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1800; scene.render.resolution_y = 1200
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.0, -0.04, 0.10))
for name, off in {
    'edges_under': Vector((0.10, -0.05, -0.24)),
    'edges_tq': Vector((0.22, -0.22, 0.12)),
    'edges_side': Vector((0.32, 0.0, 0.04)),
}.items():
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

print('A762_EDGE_MARK', len(segs), flush=True)
