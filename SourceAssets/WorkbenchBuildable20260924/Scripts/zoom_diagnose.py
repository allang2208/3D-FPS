"""Close-up diagnostic renders of the clutter: blueprint sheet, book stack, open book, tray."""
from pathlib import Path
import bpy, math
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Renders'
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Authored/StandaloneWorkbench.blend'))
ob = bpy.data.objects['SM_WBStandalone_Workbench']
for other in bpy.data.objects:
    if other.type == 'MESH' and other is not ob:
        other.hide_render = True
# report UV extents per material slot on the joined mesh
me = ob.data
print('UV_LAYERS', [l.name for l in me.uv_layers])
uvl = me.uv_layers[0]
for i, slot in enumerate(me.materials):
    if not slot:
        continue
    us = vs = None
    for p in me.polygons:
        if p.material_index != i:
            continue
        for li in p.loop_indices:
            u, v = uvl.data[li].uv
            us = (min(us[0], u), max(us[1], u)) if us else (u, u)
            vs = (min(vs[0], v), max(vs[1], v)) if vs else (v, v)
    print('SLOT', i, slot.name, 'uv_u', us and [round(x, 3) for x in us], 'uv_v', vs and [round(x, 3) for x in vs])

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'
prefs.get_devices()
for d in prefs.devices: d.use = True
scene.cycles.device = 'GPU'
scene.cycles.samples = 64
scene.render.resolution_x = 1000
scene.render.resolution_y = 700
cam_data = bpy.data.cameras.new('Cam2'); cam_data.lens = 50; cam = bpy.data.objects.new('Cam2', cam_data)
scene.collection.objects.link(cam); scene.camera = cam

def closeup(name, target, offset):
    t = Vector(target)
    cam.location = t + Vector(offset)
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)
    print('SHOT', name)

closeup('zoom-blueprint.png', (0.80, -0.20, 0.945), (-0.35, -0.30, 0.45))
closeup('zoom-books.png', (-0.67, -0.955, 0.97), (-0.45, -0.30, 0.35))
closeup('zoom-openbook.png', (-0.14, -0.985, 0.95), (-0.30, -0.32, 0.28))
print('ZOOMS_DONE')
