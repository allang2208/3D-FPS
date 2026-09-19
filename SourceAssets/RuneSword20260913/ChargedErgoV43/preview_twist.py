"""Render authored vs redistributed left forearm on the worst charged frames."""
import bpy, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twist_distribution as td

SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
OUT = P / 'ReviewTwist'
OUT.mkdir(exist_ok=True)
FPS = 480.0
SHOTS = [('HeavyCharge', 0.20), ('HeavyCharge', 0.35), ('HeavyCharge', 0.65),
         ('HeavyRelease', 0.075), ('HeavyRelease', 0.40), ('HeavyRelease', 0.60)]

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
sword = bpy.data.objects['RuneSword_Blade']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}

for ob in scene.objects:
    keep = ob in (rig, arms, sword)
    ob.hide_render = not keep
    try:
        ob.hide_set(not keep)
    except RuntimeError:
        pass

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 700
scene.render.resolution_y = 560
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('TwistReviewWorld')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.16, .18, .22, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = .9

clay = bpy.data.materials.new('TwistClay')
clay.use_nodes = True
bsdf = clay.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.60, .63, .68, 1)
bsdf.inputs['Roughness'].default_value = .58

for name, loc, energy, size in [('Key', (-.5, -.45, 1.0), 110, 1.2),
                                ('Fill', (.7, .4, .5), 65, 1.1),
                                ('Rim', (-.3, 1.1, .4), 85, .9)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.shape = 'DISK'
    light.size = size
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, .15, .05)) - ob.location).to_track_quat('-Z', 'Y').to_euler()

data = bpy.data.cameras.new('TwistCamera')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
data.clip_start = .005


def activate(clip, seconds):
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    f = seconds * FPS
    scene.frame_set(int(f), subframe=f - int(f))
    bpy.context.view_layer.update()


def apply_distribution(weight):
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    updated = td.rebuild(pose, rest, weight)
    for bone in (td.LO, td.TWIST_01, td.TWIST_02, td.HAND):
        rig.pose.bones[bone].matrix = updated[bone]
        bpy.context.view_layer.update()


def render_joint(name, raw):
    arms.data.materials.clear()
    arms.data.materials.append(raw)
    for poly in arms.data.polygons:
        poly.material_index = 0
    A, E, H = [rig.pose.bones[n].matrix.translation
               for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
    centre = (A + E + H) / 3
    camera.location = centre + Vector((-.6, -.7, .24))
    camera.rotation_euler = (Vector(centre) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'
    data.ortho_scale = .72
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)


for clip, seconds in SHOTS:
    tag = '%s_%03dms' % (clip, round(seconds * 1000))
    for label, weight in (('authored', 0.0), ('distributed', 1.0)):
        activate(clip, seconds)
        if weight > 0:
            apply_distribution(weight)
        render_joint('%s_%s' % (tag, label), clay)
        print('SHOT', tag, label, flush=True)

print('PREVIEW_TWIST_DONE', flush=True)
