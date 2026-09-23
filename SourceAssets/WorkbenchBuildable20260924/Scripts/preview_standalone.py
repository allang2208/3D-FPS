"""Preview render of the standalone subset (table+frame+lamp+bench props, no wall parts).

Run:
  "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --python-exit-code 1 \
      --python SourceAssets/WorkbenchBuildable20260924/Scripts/preview_standalone.py
"""
from pathlib import Path
import bpy, math
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
KIT = 'D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkbenchKit20260921/Authored/DungeonWorkbenchKit.blend'
OUT = ROOT / 'Renders'
OUT.mkdir(exist_ok=True)

KEEP_PREFIX = ('SM_WBK_',)
EXCLUDE_PREFIX = ('SM_WBK_Fab_Wall_', 'SM_WBK_Surface_',
                  'SM_WBK_Fab_Mounts', 'SM_WBK_Fab_LabelsRetained',
                  'SM_WBK_PowerLead', 'SM_WBK_SocketPlug')

bpy.ops.wm.open_mainfile(filepath=KIT)
shown = []
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        ob.hide_render = True; ob.hide_set(True); continue
    keep = ob.name.startswith(KEEP_PREFIX) and not ob.name.startswith(EXCLUDE_PREFIX)
    ob.hide_render = not keep
    ob.hide_set(not keep)
    if keep:
        shown.append(ob.name)
print('RENDER_SUBSET', len(shown), shown)

deps = bpy.context.evaluated_depsgraph_get()
bbox = [ob.matrix_world @ Vector(c) for ob in bpy.data.objects if not ob.hide_render and ob.type == 'MESH' for c in ob.bound_box]
cmin = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
cmax = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
center = (cmin + cmax) / 2
diag = (cmax - cmin).length
print('ASSEMBLY_BOUNDS_CM', [round(v * 100, 1) for v in cmin], [round(v * 100, 1) for v in cmax])

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dtype in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = dtype
            prefs.get_devices()
            if any(d.type == dtype for d in prefs.devices):
                for d in prefs.devices: d.use = True
                scene.cycles.device = 'GPU'
                print('BAKE_DEVICE', dtype)
                break
        except Exception as e:
            print('DEVICE_FAIL', dtype, e)
except Exception as e:
    print('GPU_SETUP_ERROR', e)
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1100
scene.render.resolution_y = 800
scene.view_settings.look = 'AgX - Base Contrast' if 'AgX' in scene.view_settings.view_transform else scene.view_settings.look

world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
if bg: bg.inputs[0].default_value = (0.35, 0.38, 0.42, 1); bg.inputs[1].default_value = 0.5

cam_data = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam); scene.camera = cam

def shoot(name, direction, dist, elev_deg, target=None):
    t = target or center
    e = math.radians(elev_deg)
    d = Vector((direction[0] * math.cos(e), direction[1] * math.cos(e), math.sin(e))).normalized()
    cam.location = t + d * (dist * diag)
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)
    print('SHOT', name)

shoot('preview-front.png', (-0.75, -0.60, 0.42), 1.45, 0)
shoot('preview-back.png', (0.75, 0.60, 0.42), 1.45, 0)
shoot('preview-top.png', (0.06, -0.04, 1.0), 1.02, 0, target=Vector((center.x, center.y, 0.94)))
print('PREVIEW_DONE')
