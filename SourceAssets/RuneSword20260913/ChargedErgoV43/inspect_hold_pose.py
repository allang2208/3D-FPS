"""Close inspection of the left arm at the charged hold pose."""
import bpy, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
OUT = P / 'ReviewHold'
OUT.mkdir(exist_ok=True)
FPS = 480.0
BLENDS = {'before': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
          'v44': P / 'AzureRunesword_ChargedShoulderV44.blend'}
RIGHT = ('upperarm_r', 'lowerarm_r', 'hand_r', 'clavicle_r',
         'lowerarm_twist_01_r', 'lowerarm_twist_02_r',
         'upperarm_twist_01_r', 'upperarm_twist_02_r')


def build(label, path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
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
    scene.render.resolution_x = 900
    scene.render.resolution_y = 700
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('HoldWorld' + label)
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.28, .32, .38, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 1.1
    for name, loc, energy, size in [('Key', (-.5, -.4, 1.1), 130, 1.3),
                                    ('Fill', (.8, .4, .6), 80, 1.2),
                                    ('Rim', (-.3, 1.2, .4), 100, .9)]:
        light = bpy.data.lights.new(name + label, 'AREA')
        light.energy = energy
        light.shape = 'DISK'
        light.size = size
        ob = bpy.data.objects.new(name + label, light)
        scene.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector((0, .2, .1)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    data = bpy.data.cameras.new('HoldCamera' + label)
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.clip_start = .005
    action = bpy.data.actions['A_RuneSword_HeavyCharge']
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for seconds in (1.60, 1.80, 1.95, 2.00):
        f = seconds * FPS
        scene.frame_set(int(f), subframe=f - int(f))
        bpy.context.view_layer.update()
        tag = '%04dms' % round(seconds * 1000)
        camera.location = (0, 0, 0)
        camera.rotation_euler = Vector((0.02, 1.0, -0.06)).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'PERSP'
        data.lens = 17
        scene.render.filepath = str(OUT / ('%s_%s_fp.png' % (tag, label)))
        bpy.ops.render.render(write_still=True)
        if seconds == 2.00:
            A, E, H = [rig.pose.bones[n].matrix.translation
                       for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
            centre = (A + E + H) / 3
            for name, offset in (('front', Vector((0, -1.4, .2))),
                                 ('back', Vector((0, 1.4, .2))),
                                 ('outside', Vector((-1.4, -.2, .1))),
                                 ('inside', Vector((.9, -.5, -.4))),
                                 ('top', Vector((-.1, -.2, 1.5)))):
                camera.location = centre + offset.normalized() * 1.2
                camera.rotation_euler = (Vector(centre) - camera.location).to_track_quat('-Z', 'Y').to_euler()
                data.type = 'ORTHO'
                data.ortho_scale = .68
                scene.render.filepath = str(OUT / ('%s_%s_%s.png' % (tag, name, label)))
                bpy.ops.render.render(write_still=True)
        print('SHOT', tag, label, flush=True)


for label, path in BLENDS.items():
    build(label, path)
print('INSPECT_HOLD_DONE', flush=True)
