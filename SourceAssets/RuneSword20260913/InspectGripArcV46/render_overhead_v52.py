"""Render V52 key frames: does the raised hold keep the view usable?"""
import bpy, math
from pathlib import Path

P = Path(__file__).parent
SOURCE = P / 'AzureRunesword_OverheadV52.blend'
CLIP = 'A_RuneSword_Overhead'
FPS = 120.0
TIMES = (0.00, 0.30, 0.55, 0.63, 0.75, 0.90, 1.05, 1.15, 1.22, 1.30, 1.38, 1.50, 1.80, 2.60)
OUT = P / 'ReviewV52'
OUT.mkdir(exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
blade = bpy.data.objects['RuneSword_Blade']
action = bpy.data.actions[CLIP]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
for ob in list(scene.objects):
    keep = ob in (rig, arms, blade)
    ob.hide_render = not keep
    if keep:
        ob.hide_set(False)
        ob.hide_viewport = False
arms.color = (0.52, 0.66, 0.76, 1)
blade.color = (0.60, 0.40, 0.14, 1)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.show_backface_culling = True
scene.display.shading.background_type = 'WORLD'
scene.world.color = (0.05, 0.06, 0.08)
scene.render.resolution_x, scene.render.resolution_y = 640, 400
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
data = bpy.data.cameras.new('CheckCamera')
camera = bpy.data.objects.new('CheckCamera', data)
scene.collection.objects.link(camera)
camera.location = (0, 0, 0)
camera.rotation_euler = (math.pi / 2, 0, 0)
data.sensor_fit = 'VERTICAL'
data.sensor_height = 24
data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
data.clip_start = 0.005
scene.camera = camera
for seconds in TIMES:
    frame = seconds * FPS
    scene.frame_set(int(frame), subframe=frame - int(frame))
    scene.render.filepath = str(OUT / ('chop_%04d.png' % round(seconds * 1000)))
    bpy.ops.render.render(write_still=True)
print('RENDER_OVERHEAD_V52_DONE')
