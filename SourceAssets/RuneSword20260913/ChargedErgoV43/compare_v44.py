"""Render V22 baseline vs V44: eye point, elbow close-up and shoulder view."""
import bpy
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
OUT = P / 'ReviewV44'
OUT.mkdir(exist_ok=True)
FPS = 480.0
BLENDS = {'before': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
          'v44': P / 'AzureRunesword_ChargedShoulderV44.blend'}
SHOTS = [('HeavyCharge', 0.20), ('HeavyCharge', 0.35), ('HeavyCharge', 0.65),
         ('HeavyRelease', 0.60)]


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
    scene.render.resolution_x = 820
    scene.render.resolution_y = 560
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('V44World' + label)
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.30, .34, .40, 1)
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
    data = bpy.data.cameras.new('V44Camera' + label)
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.clip_start = .005
    for clip, seconds in SHOTS:
        action = bpy.data.actions['A_RuneSword_' + clip]
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        f = seconds * FPS
        scene.frame_set(int(f), subframe=f - int(f))
        bpy.context.view_layer.update()
        tag = '%s_%03dms' % (clip, round(seconds * 1000))
        camera.location = (0, 0, 0)
        camera.rotation_euler = Vector((0.02, 1.0, -0.06)).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'PERSP'
        data.lens = 17
        scene.render.filepath = str(OUT / ('%s_%s_fp.png' % (tag, label)))
        bpy.ops.render.render(write_still=True)
        A, E, H = [rig.pose.bones[n].matrix.translation
                   for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
        centre = (A + E + H) / 3
        camera.location = centre + Vector((-.6, -.7, .24))
        camera.rotation_euler = (Vector(centre) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'ORTHO'
        data.ortho_scale = .72
        scene.render.filepath = str(OUT / ('%s_%s_joint.png' % (tag, label)))
        bpy.ops.render.render(write_still=True)
        shoulder = rig.pose.bones['upperarm_l'].matrix.translation
        centre2 = shoulder + Vector((-.02, 0, -.05))
        camera.location = centre2 + Vector((.35, -.55, .18))
        camera.rotation_euler = (Vector(centre2) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        data.ortho_scale = .42
        scene.render.filepath = str(OUT / ('%s_%s_shoulder.png' % (tag, label)))
        bpy.ops.render.render(write_still=True)
        print('SHOT', tag, label, flush=True)


for label, path in BLENDS.items():
    build(label, path)
print('COMPARE_V44_DONE', flush=True)
