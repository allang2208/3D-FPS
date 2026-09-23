"""Render the authored standalone workbench blend from four angles."""
from pathlib import Path
import bpy, math
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
BLEND = str(ROOT / 'Authored/StandaloneWorkbench.blend')
OUT = ROOT / 'Renders'
OUT.mkdir(exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
ob = bpy.data.objects['SM_WBStandalone_Workbench']
for other in bpy.data.objects:
    if other.type == 'MESH' and other is not ob:
        other.hide_render = True
        other.hide_set(True)
ob.hide_render = False

bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
cmin = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
cmax = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
center = (cmin + cmax) / 2
diag = (cmax - cmin).length

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
for dtype in ('OPTIX', 'CUDA'):
    try:
        prefs.compute_device_type = dtype
        prefs.get_devices()
        if any(d.type == dtype for d in prefs.devices):
            for d in prefs.devices: d.use = True
            scene.cycles.device = 'GPU'
            break
    except Exception:
        continue
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1100
scene.render.resolution_y = 800

world = scene.world
bg = world.node_tree.nodes.get('Background')
if bg: bg.inputs[0].default_value = (0.5, 0.52, 0.55, 1); bg.inputs[1].default_value = 0.7

cam_data = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam); scene.camera = cam

def shoot(name, direction, dist, target=None):
    t = target or center
    d = Vector(direction).normalized()
    cam.location = t + d * (dist * diag)
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)
    print('SHOT', name)

shoot('built-front.png', (-0.72, -0.62, 0.40), 1.35)
shoot('built-desk.png', (-0.55, -0.45, 0.85), 0.95, target=Vector((center.x, center.y, 0.94)))
shoot('built-return.png', (-0.85, -0.35, 0.42), 0.62, target=Vector((-0.67, -0.955, 0.97)))
shoot('built-back.png', (0.72, 0.62, 0.40), 1.35)
print('BUILT_RENDERS_DONE')
