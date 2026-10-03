"""Per-frame screen coverage of the support arm against the game camera anchor.

Flat shading + exact object colours make the coverage a pixel count, not an eyeball
estimate. Prints the coverage curve for the whole reload so the offending window is
identified before any authoring change.
"""
import bpy, json, math, sys
from pathlib import Path
import numpy as np

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CLIP = ARGS[0] if ARGS else 'reload'
STEP = int(ARGS[1]) if len(ARGS) > 1 else 2
OVERRIDE_BLEND = ARGS[2] if len(ARGS) > 2 else None
OVERRIDE_ACTION = ARGS[3] if len(ARGS) > 3 else None
JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925')
OUT = JOB / 'Review' / 'coverage'
OUT.mkdir(parents=True, exist_ok=True)

CLIPS = {
    'reload': (r'D:\FPS3D\FPSGAME\SourceAssets\SVDThumbUp20260923\SVD_base_Editable.blend', 'A_SVD_reload', 400),
    'reload_empty': (r'D:\FPS3D\FPSGAME\SourceAssets\SVDChargeGrasp20260924\SVD_base_Grasp.blend', 'A_SVD_reload_empty', 515),
}
blend, action, LAST = CLIPS[CLIP]
if OVERRIDE_BLEND:
    blend, action = OVERRIDE_BLEND, OVERRIDE_ACTION
TAG = ARGS[4] if len(ARGS) > 4 else CLIP
RANGE = [int(v) for v in ARGS[5].split(',')] if len(ARGS) > 5 and ',' in ARGS[5] else None
bpy.ops.wm.open_mainfile(filepath=blend, use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[action]
scene = bpy.context.scene

ARM_RGB = np.array([0.55, 0.63, 0.70]) * 255.0
cam = bpy.data.objects.new('CoverageCam', bpy.data.cameras.new('CoverageCam'))
scene.collection.objects.link(cam)
cam.location = (0.0, -0.10, 0.05)
cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
cam.data.clip_start = 0.005
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 24
cam.data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
scene.camera = cam
for ob in scene.objects:
    if ob.type == 'MESH':
        # Support arm only: the coverage count is then simply non-background pixels.
        ob.hide_render = ob != arms
        ob.color = (.55, .63, .70, 1)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'FLAT'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_backface_culling = False
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = False
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0
if not scene.world:
    scene.world = bpy.data.worlds.new('CoverageWorld')
scene.world.color = (0.0, 0.0, 0.0)
scene.render.resolution_x = 620
scene.render.resolution_y = 260
scene.render.image_settings.file_format = 'PNG'
bpy.context.view_layer.update()

rows = []
FRAME_LIST = (list(range(RANGE[0], RANGE[1] + 1, STEP)) if RANGE
              else list(range(0, LAST + 1, STEP)) + [LAST])
for f in FRAME_LIST:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(f)
    bpy.context.view_layer.update()
    path = OUT / f'{TAG}_{f:03d}.png'
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    shot = bpy.data.images.load(str(path))
    buf = np.empty(len(shot.pixels), dtype=np.float32)
    shot.pixels.foreach_get(buf)
    img = buf.reshape(shot.size[1], shot.size[0], 4)[..., :3] * 255.0
    bpy.data.images.remove(shot)
    arm_px = int((img.sum(axis=2) > 30).sum())
    total = img.shape[0] * img.shape[1]
    rows.append((f, arm_px, arm_px / total))
    path.unlink()
worst = sorted(rows, key=lambda r: -r[2])[:12]
print('COVERAGE_WORST', json.dumps([(f, round(v, 4)) for f, _, v in worst]), flush=True)
prev = None
for f, px, frac in rows:
    if frac > 0.02:
        print(f'COVERAGE {TAG} frame {f:4d} px {px:7d} frac {frac:.4f}', flush=True)
(JOB / f'coverage_{TAG}.json').write_text(json.dumps(
    [{'frame': f, 'arm_pixels': px, 'fraction': round(v, 5)} for f, px, v in rows], indent=1))
