"""Render V46 and V47 at the reference timestamps for a three-way comparison."""
import bpy, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCES = {
    'v46': P / 'AzureRunesword_InspectGripArcV46.blend',
    'v47': P / 'AzureRunesword_InspectTwirlV47.blend',
}
PHASES = [0.350, 0.383, 0.417, 0.450, 0.483, 0.517, 0.550, 0.583, 0.617, 0.650,
          0.700, 0.800]
FPS = 120.0
OUT = P / 'ReviewV47'
OUT.mkdir(exist_ok=True)

for label, path in SOURCES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    blade = bpy.data.objects['RuneSword_Blade']
    action = bpy.data.actions['A_RuneSword_Inspect']
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
    scene.render.resolution_x, scene.render.resolution_y = 852, 480
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    data = bpy.data.cameras.new('CompareCamera')
    camera = bpy.data.objects.new('CompareCamera', data)
    scene.collection.objects.link(camera)
    camera.location = (0, 0, 0)
    camera.rotation_euler = (math.pi / 2, 0, 0)
    data.sensor_fit = 'VERTICAL'
    data.sensor_height = 24
    data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
    data.clip_start = 0.005
    scene.camera = camera
    for seconds in PHASES:
        frame = seconds * FPS
        scene.frame_set(int(frame), subframe=frame - int(frame))
        scene.render.filepath = str(OUT / ('%s_%04d.png' % (label, round(seconds * 1000))))
        bpy.ops.render.render(write_still=True)
    print('RENDERED', label, flush=True)
print('TWIRL_V47_RENDER_DONE')
