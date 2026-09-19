"""Tight elbow views at the charged hold, left against right."""
import bpy
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
OUT = P / 'ReviewElbow'
OUT.mkdir(exist_ok=True)
FPS = 480.0
BLEND = P / 'AzureRunesword_ChargedShoulderV44.blend'
SECONDS = (1.80, 2.00)

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
sword = bpy.data.objects['RuneSword_Blade']
for ob in scene.objects:
    keep = ob in (rig, arms, sword)
    ob.hide_render = not keep
    try:
        ob.hide_set(not keep)
    except RuntimeError:
        pass

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 780
scene.render.resolution_y = 640
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('ElbowWorld')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.26, .30, .36, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 1.2
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
data = bpy.data.cameras.new('ElbowCamera')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
data.clip_start = .002
data.type = 'ORTHO'

action = bpy.data.actions['A_RuneSword_HeavyCharge']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]

VIEWS = (('outside', Vector((-1.0, -.5, .15))), ('inside', Vector((.9, -.7, -.2))),
         ('up', Vector((0, -.3, 1.3))), ('down', Vector((0, -.3, -1.3))))

for seconds in SECONDS:
    scene.frame_set(int(round(seconds * FPS)))
    bpy.context.view_layer.update()
    for side in ('l', 'r'):
        S = rig.pose.bones['upperarm_' + side].matrix.translation
        E = rig.pose.bones['lowerarm_' + side].matrix.translation
        W = rig.pose.bones['hand_' + side].matrix.translation
        centre = (S + 2 * E + W) / 4
        for name, offset in VIEWS:
            camera.location = centre + offset.normalized() * .6
            camera.rotation_euler = (Vector(centre) - camera.location).to_track_quat('-Z', 'Y').to_euler()
            data.ortho_scale = .30
            scene.render.filepath = str(OUT / ('%04dms_%s_%s.png'
                                               % (round(seconds * 1000), side, name)))
            bpy.ops.render.render(write_still=True)
    print('SHOT', seconds, flush=True)
print('ELBOW_HOLD_DONE', flush=True)
