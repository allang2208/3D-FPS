"""Full-size in-game-eye renders of the charged raise for close inspection."""
import bpy
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
OUT = P / 'ReviewLarge'
OUT.mkdir(exist_ok=True)
FPS = 480.0
SHOTS = [('HeavyCharge', 0.0), ('HeavyCharge', 0.20), ('HeavyCharge', 0.35),
         ('HeavyCharge', 0.65), ('HeavyCharge', 2.00), ('HeavyRelease', 0.075)]

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
for ob in scene.objects:
    keep = ob in (rig, bpy.data.objects['SK_Manny_Arms_Export'], bpy.data.objects['RuneSword_Blade'])
    ob.hide_render = not keep
    try:
        ob.hide_set(not keep)
    except RuntimeError:
        pass

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 800
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('LargeWorld')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.30, .34, .40, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 1.1

for name, loc, energy, size in [('Key', (-.5, -.4, 1.1), 130, 1.3),
                                ('Fill', (.8, .4, .6), 80, 1.2),
                                ('Rim', (-.3, 1.2, .4), 100, .9)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.shape = 'DISK'
    light.size = size
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, .2, .1)) - ob.location).to_track_quat('-Z', 'Y').to_euler()

data = bpy.data.cameras.new('LargeCamera')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
data.lens = 17
data.clip_start = .005
camera.location = (0, 0, 0)
camera.rotation_euler = (Vector((0.02, 1.0, -0.06))).to_track_quat('-Z', 'Y').to_euler()

for clip, seconds in SHOTS:
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    f = seconds * FPS
    scene.frame_set(int(f), subframe=f - int(f))
    bpy.context.view_layer.update()
    scene.render.filepath = str(OUT / ('%s_%03dms.png' % (clip, round(seconds * 1000))))
    bpy.ops.render.render(write_still=True)
    print('SHOT', clip, seconds, flush=True)

print('RENDER_LARGE_DONE', flush=True)
