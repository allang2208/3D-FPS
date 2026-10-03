"""Render the SVD reload return segment and measure the support arm's screen coverage.

Numbers use the game camera anchor used by the accepted SVD reviews (0,-0.10,0.05) m,
125 mm behind the mesh root along -Y and 50 mm up, 75 deg vertical FOV, 5 mm near clip.
Coverage is counted from the rendered pixels (arm colour vs weapon vs background) so a
stale matrix or a bad projection cannot fake the result.
"""
import bpy, json, math, sys
from pathlib import Path
import numpy as np

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CLIP = ARGS[0] if ARGS else 'reload'
FRAMES = [int(v) for v in ARGS[1:] if v.lstrip('-').isdigit()] or [320, 326, 332, 338, 344, 352, 360, 380, 400]
JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925')
OUT = JOB / 'Review'
OUT.mkdir(parents=True, exist_ok=True)

CLIPS = {
    'reload': (r'D:\FPS3D\FPSGAME\SourceAssets\SVDThumbUp20260923\SVD_base_Editable.blend', 'A_SVD_reload'),
    'reload_empty': (r'D:\FPS3D\FPSGAME\SourceAssets\SVDChargeGrasp20260924\SVD_base_Grasp.blend', 'A_SVD_reload_empty'),
}
blend, action = CLIPS[CLIP]
EXTRA = [a for a in ARGS[1:] if not a.lstrip('-').isdigit()]
if len(EXTRA) >= 2:
    blend, action = EXTRA[0], EXTRA[1]
TAG = EXTRA[2] if len(EXTRA) > 2 else CLIP
bpy.ops.wm.open_mainfile(filepath=blend, use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[action]
scene = bpy.context.scene

LEFT_BONES = ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l',
              'upperarm_twist_01_l', 'upperarm_twist_02_l',
              'lowerarm_twist_01_l', 'lowerarm_twist_02_l')
LEFT_GROUPS = {g.index for g in arms.vertex_groups if g.name in LEFT_BONES}
left_ids = [v.index for v in arms.data.vertices
            if sum(g.weight for g in v.groups if g.group in LEFT_GROUPS)
            / max(1e-8, sum(g.weight for g in v.groups)) > 0.9]

ARM_RGB = np.array([0.55, 0.63, 0.70]) * 255.0
WPN_RGB = np.array([0.20, 0.23, 0.27]) * 255.0
BG_RGB = np.array([0.055, 0.065, 0.08]) * 255.0

cam = bpy.data.objects.new('ReportCam', bpy.data.cameras.new('ReportCam'))
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
        ob.hide_render = not any(m.type == 'ARMATURE' and m.object == rig for m in ob.modifiers)
        ob.color = (.55, .63, .70, 1) if ob == arms else (.20, .23, .27, 1)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_backface_culling = False
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
if not scene.world:
    scene.world = bpy.data.worlds.new('ReportWorld')
scene.world.color = (.055, .065, .08)
scene.render.resolution_x = 1240
scene.render.resolution_y = 520
scene.render.image_settings.file_format = 'PNG'
bpy.context.view_layer.update()
TO_CAM = cam.matrix_world.inverted()
CAM_ROT = cam.matrix_world.to_3x3()
print('CAM matrix', [round(v, 4) for row in cam.matrix_world for v in row], flush=True)

report = {}
for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = arms.evaluated_get(dg)
    mw = ev.matrix_world
    pts = [TO_CAM @ (mw @ ev.data.vertices[i].co) for i in left_ids]
    eye = [p.length for p in pts]
    fwd = [-p.z for p in pts]
    path = OUT / f'{TAG}_leftarm_{f:03d}.png'
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    shot = bpy.data.images.load(str(path))
    buf = np.empty(len(shot.pixels), dtype=np.float32)
    shot.pixels.foreach_get(buf)
    img = buf.reshape(shot.size[1], shot.size[0], 4)[..., :3] * 255.0
    bpy.data.images.remove(shot)
    dist_arm = np.abs(img - ARM_RGB).sum(axis=2)
    arm_px = int((dist_arm < 60).sum())
    report[f] = dict(min_eye_mm=round(min(eye) * 1000, 1),
                     min_fwd_mm=round(min(fwd) * 1000, 1),
                     behind_eye=int(sum(1 for v in fwd if v < 0)),
                     within_120mm=int(sum(1 for v in fwd if 0 <= v < 0.12)),
                     arm_pixels=arm_px,
                     arm_frame_fraction=round(arm_px / img.shape[0] / img.shape[1], 4))
(JOB / f'render_report_{TAG}.json').write_text(json.dumps(report, indent=1))
for f, r in report.items():
    print('LEFT_ARM_FRAME', TAG, f, json.dumps(r), flush=True)
