"""Render the left elbow at charged-attack key times for joint inspection."""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
OUT = P / 'Review'
OUT.mkdir(exist_ok=True)
FPS = 480.0

SHOTS = [
    ('HeavyCharge', 0.00), ('HeavyCharge', 0.12), ('HeavyCharge', 0.20),
    ('HeavyCharge', 0.35), ('HeavyCharge', 0.65), ('HeavyCharge', 1.00),
    ('HeavyCharge', 1.40), ('HeavyCharge', 1.60), ('HeavyCharge', 2.00),
    ('HeavyRelease', 0.02), ('HeavyRelease', 0.075), ('HeavyRelease', 0.15),
    ('HeavyRelease', 0.40), ('HeavyRelease', 0.60), ('HeavyRelease', 0.80),
    ('HeavyRelease', 1.00),
]

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
scene.render.resolution_x = 900
scene.render.resolution_y = 560
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'

world = bpy.data.worlds.new('ChargedErgoV43World')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.14, .16, .20, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = .6

clay = bpy.data.materials.new('LeftArmInspectionClay')
clay.use_nodes = True
bsdf = clay.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.58, .62, .68, 1)
bsdf.inputs['Roughness'].default_value = .62
arms.data.materials.clear()
arms.data.materials.append(clay)
for poly in arms.data.polygons:
    poly.material_index = 0

for name, loc, energy, size in [('Key', (-.5, -.35, 1.0), 90, 1.2),
                                ('Fill', (.7, .3, .6), 55, 1.1),
                                ('Rim', (-.2, 1.1, .5), 70, .8)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.shape = 'DISK'
    light.size = size
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, .2, .1)) - ob.location).to_track_quat('-Z', 'Y').to_euler()

data = bpy.data.cameras.new('LeftArmCamera')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
data.lens = 20
data.clip_start = .005


def activate(clip, seconds):
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    f = seconds * FPS
    scene.frame_set(int(f), subframe=f - int(f))
    bpy.context.view_layer.update()


def shoot(name, position, target, scale):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'
    data.ortho_scale = scale
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)


for clip, seconds in SHOTS:
    activate(clip, seconds)
    tag = '%s_%03dms' % (clip, round(seconds * 1000))
    A, E, H = [rig.matrix_world @ rig.pose.bones[n].matrix.translation
               for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
    # Same framing as the accepted V21/V22 joint review images.
    centre = (A + E + H) / 3
    shoot(tag + '_left_joint', centre + Vector((-.6, -.7, .24)), centre, .72)
    print('SHOT', tag, flush=True)

print('RENDER_DONE', flush=True)
