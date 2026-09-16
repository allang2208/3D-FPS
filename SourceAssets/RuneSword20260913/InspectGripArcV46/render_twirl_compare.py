"""Render the shipped V42 Inspect at the reference timestamps, next to the video frames.

Reference timeline: the shipped clip maps video 76.000 s to clip 0.350 s, so
clip_time = 0.350 + (video_time - 76.000).  Frames are rendered from the project
viewmodel camera (origin, +Y forward, 75 deg vertical FOV) in workbench clay.
"""
import bpy, math
from pathlib import Path

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
REF = P.parent / 'VideoReferenceStudy20260915/Original'
OUT = P / 'TwirlCompare'
OUT.mkdir(exist_ok=True)
FPS = 120.0
# (reference frame index in VideoReferenceStudy20260915/Original, video seconds)
PHASES = [(7, 76.0000), (8, 76.0333), (9, 76.0667), (10, 76.1000), (11, 76.1333),
          (12, 76.1667), (13, 76.2000), (14, 76.2333), (15, 76.2667), (16, 76.3000),
          (17, 76.3333), (19, 76.4000), (20, 76.4333), (21, 76.4667)]

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
blade = bpy.data.objects['RuneSword_Blade']
action = bpy.data.actions['A_RuneSword_Inspect']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]

for ob in scene.objects:
    keep = ob in (rig, arms, blade)
    ob.hide_render = not keep
    if keep:
        ob.hide_set(False)
        ob.hide_viewport = False
arms.color = (0.48, 0.63, 0.74, 1)
blade.color = (0.58, 0.38, 0.12, 1)

scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.show_backface_culling = True
scene.display.shading.background_type = 'WORLD'
scene.world.color = (0.04, 0.05, 0.065)
scene.render.resolution_x = 852
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False

data = bpy.data.cameras.new('TwirlCompareCamera')
camera = bpy.data.objects.new('TwirlCompareCamera', data)
scene.collection.objects.link(camera)
camera.location = (0, 0, 0)
camera.rotation_euler = (math.pi / 2, 0, 0)
data.sensor_fit = 'VERTICAL'
data.sensor_height = 24
data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
data.clip_start = 0.005
scene.camera = camera

for index, seconds in PHASES:
    t = 0.350 + (seconds - 76.0000)
    f = t * FPS
    scene.frame_set(int(f), subframe=f - int(f))
    scene.render.filepath = str(OUT / ('v42_%02d_%07.4f.png' % (index, seconds)))
    bpy.ops.render.render(write_still=True)
    print('RENDERED', index, seconds, t, flush=True)

print('TWIRL_COMPARE_RENDER_DONE')
