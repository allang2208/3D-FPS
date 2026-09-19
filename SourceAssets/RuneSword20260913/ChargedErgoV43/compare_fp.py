"""Render V22 (before) and V43 (after) from the eye point and a forearm close-up."""
import bpy, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
OUT = P / 'ReviewCompare'
OUT.mkdir(exist_ok=True)
FPS = 480.0
BLENDS = {'before': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
          'after': P / 'AzureRunesword_ChargedErgoV43.blend'}
SHOTS = [('HeavyCharge', 0.20), ('HeavyCharge', 0.35), ('HeavyCharge', 0.50),
         ('HeavyCharge', 0.65), ('HeavyRelease', 0.60)]


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
    scene.render.resolution_y = 620
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('CompareWorld' + label)
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
    data = bpy.data.cameras.new('CompareCamera' + label)
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
        # Eye point, matching the in-game viewmodel camera.
        camera.location = (0, 0, 0)
        camera.rotation_euler = Vector((0.02, 1.0, -0.06)).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'PERSP'
        data.lens = 17
        scene.render.filepath = str(OUT / ('%s_%s_fp.png' % (tag, label)))
        bpy.ops.render.render(write_still=True)
        # Fixed close-up on the left forearm so an axial rotation is readable.
        E, H = [rig.pose.bones[n].matrix.translation for n in ('lowerarm_l', 'hand_l')]
        centre = (E + H) / 2
        axis = (H - E).normalized()
        side = axis.cross(Vector((0, 0, 1)))
        side = side.normalized() if side.length > 1e-4 else Vector((1, 0, 0))
        top = axis.cross(side).normalized()
        camera.location = centre + side * .45 + top * .12
        camera.rotation_euler = (Vector(centre) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'ORTHO'
        data.ortho_scale = .34
        scene.render.filepath = str(OUT / ('%s_%s_close.png' % (tag, label)))
        bpy.ops.render.render(write_still=True)
        print('SHOT', tag, label, flush=True)


for label, path in BLENDS.items():
    build(label, path)
print('COMPARE_FP_DONE', flush=True)
