"""Render the V53 inspect from the viewmodel camera for a review GIF."""
import bpy
import math
from pathlib import Path

P = Path(__file__).parent
SOURCE = P / 'AzureRunesword_InspectFaceTurnV53.blend'
OUT = P / 'ReviewV53'
OUT.mkdir(exist_ok=True)
FPS = 120.0
GIF_FPS = 12.0
DURATION = 3.05

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
blade = bpy.data.objects['RuneSword_Blade']
action = bpy.data.actions['A_RuneSword_Inspect']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
for ob in list(scene.objects):
    keep = ob in (arms, blade)
    ob.hide_render = not keep
    if keep:
        ob.hide_set(False)
        ob.hide_viewport = False
arms.color = (0.72, 0.58, 0.48, 1)
blade.color = (0.45, 0.62, 0.78, 1)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.show_backface_culling = True
scene.display.shading.background_type = 'WORLD'
scene.world.color = (0.05, 0.06, 0.08)
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
data = bpy.data.cameras.new('ReviewCamera')
camera = bpy.data.objects.new('ReviewCamera', data)
scene.collection.objects.link(camera)
camera.location = (0, 0, 0)
camera.rotation_euler = (math.pi / 2, 0, 0)
data.sensor_fit = 'VERTICAL'
data.sensor_height = 24
data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
data.clip_start = 0.005
scene.camera = camera
count = int(round(DURATION * GIF_FPS))
for index in range(count):
    seconds = index / GIF_FPS
    frame = seconds * FPS
    scene.frame_set(int(frame), subframe=frame - int(frame))
    scene.render.filepath = str(OUT / ('frame_%03d.png' % index))
    bpy.ops.render.render(write_still=True)
print('V53_GIF_FRAMES', count)
