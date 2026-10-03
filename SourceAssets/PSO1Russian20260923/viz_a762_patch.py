"""Paint new patch faces red on bottomseal trial; re-render; pixel-diff vs pristine."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_PATCH = 0.1024, 0.02025

# Open bottomseal trial
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'PSO1_A762_bottomseal_trial.blend'))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world

# Ensure 2 materials: 0 existing, 1 red marker
if len(body.data.materials) == 0:
    body.data.materials.append(bpy.data.materials.new('BodyMat'))
mat_red = bpy.data.materials.new('PatchRed')
mat_red.use_nodes = False
try:
    mat_red.diffuse_color = (1.0, 0.05, 0.05, 1.0)
except Exception:
    pass
# workbench uses material color
if hasattr(mat_red, 'diffuse_color'):
    mat_red.diffuse_color = (1.0, 0.05, 0.05, 1.0)
while len(body.data.materials) < 2:
    body.data.materials.append(None)
body.data.materials[1] = mat_red

# Mark faces near R_PATCH as slot 1
marked = 0
for p in body.data.polygons:
    # center in delta space
    # approx from vertex average
    co = Vector((0,0,0))
    for vi in p.vertices:
        co += (mw @ body.data.vertices[vi].co) - DELTA
    co /= len(p.vertices)
    r = math.hypot(co.x, co.z - AXIS_Z)
    if abs(r - R_PATCH) < 0.0008 and -0.100 < co.y < 0.035:
        # angular in bottom/mount sector
        a = math.degrees(math.atan2(co.z - AXIS_Z, co.x))
        if -160 < a < 35:
            p.material_index = 1
            marked += 1

# Also check normals of marked faces
outward = inward = 0
for p in body.data.polygons:
    if p.material_index != 1:
        continue
    co = Vector((0,0,0))
    for vi in p.vertices:
        co += (mw @ body.data.vertices[vi].co) - DELTA
    co /= len(p.vertices)
    radial = Vector((co.x, 0, co.z - AXIS_Z))
    # normal in world
    n = mw.to_3x3() @ p.normal
    if n.dot(radial) >= 0:
        outward += 1
    else:
        inward += 1

for ob in scene.objects:
    if ob.type == 'MESH':
        keep = ob.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens')
        ob.hide_render = not keep; ob.hide_set(not keep)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1700; scene.render.resolution_y = 1100
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
# remove old cameras
for o in list(scene.objects):
    if o.type == 'CAMERA':
        bpy.data.objects.remove(o, do_unlink=True)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.01, -0.04, 0.09))
for name, off, hide_m in [
    ('patchvis_under', Vector((0.12, -0.05, -0.22)), False),
    ('patchvis_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('patchvis_side', Vector((0.30, 0.0, 0.03)), False),
    ('patchvis_tq', Vector((0.22, -0.22, 0.12)), True),
]:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

report = {'marked': marked, 'outward': outward, 'inward': inward}
(OUT / 'a762_patchvis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PATCHVIS', json.dumps(report), flush=True)
