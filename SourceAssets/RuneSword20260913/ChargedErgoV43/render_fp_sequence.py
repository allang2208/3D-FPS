"""Render the charged attack from the in-game eye point and a fixed outside view."""
import bpy
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
OUT = P / 'ReviewFP'
OUT.mkdir(exist_ok=True)
FPS = 480.0

SHOTS = [(clip, t / 1000.0) for clip, times in (
    ('HeavyCharge', (0, 120, 200, 300, 400, 500, 650, 900, 1200, 1600, 2000)),
    ('HeavyRelease', (20, 75, 150, 400, 600, 800, 1000)),
) for t in times]

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
blade = bpy.data.objects['RuneSword_Blade']

for ob in scene.objects:
    keep = ob in (rig, arms, blade)
    ob.hide_render = not keep
    try:
        ob.hide_set(not keep)
    except RuntimeError:
        pass

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 720
scene.render.resolution_y = 450
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'

world = bpy.data.worlds.new('ChargedErgoFPWorld')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.32, .36, .42, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 1.0

for name, loc, energy, size in [('Key', (-.5, -.35, 1.0), 120, 1.2),
                                ('Fill', (.7, .3, .6), 70, 1.1),
                                ('Rim', (-.2, 1.1, .5), 90, .8)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.shape = 'DISK'
    light.size = size
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, .2, .1)) - ob.location).to_track_quat('-Z', 'Y').to_euler()

data = bpy.data.cameras.new('ReviewCamera')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
data.clip_start = .005

EYE = Vector((0.0, 0.0, 0.0))
OUTSIDE = Vector((0.9, -0.55, 0.15))


def activate(clip, seconds):
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    f = seconds * FPS
    scene.frame_set(int(f), subframe=f - int(f))
    bpy.context.view_layer.update()


def shoot(name, position, target, lens):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'PERSP'
    data.lens = lens
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)


for clip, seconds in SHOTS:
    activate(clip, seconds)
    tag = '%s_%03dms' % (clip, round(seconds * 1000))
    shoot(tag + '_fp', EYE, Vector((0.05, 1.0, -0.08)), 17)
    centre = Vector((-.30, -.05, -.38))
    camera.location = centre + OUTSIDE * .6
    camera.rotation_euler = (centre - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.lens = 32
    scene.render.filepath = str(OUT / (tag + '_outside.png'))
    bpy.ops.render.render(write_still=True)
    print('SHOT', tag, flush=True)

print('RENDER_FP_DONE', flush=True)
