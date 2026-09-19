"""Render the left arm alone (right-side vertices moved aside in a temp copy)."""
import bpy
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
OUT = P / 'ReviewLeftOnly'
OUT.mkdir(exist_ok=True)
FPS = 480.0
RIGHT = ('upperarm_r', 'lowerarm_r', 'hand_r', 'clavicle_r',
         'lowerarm_twist_01_r', 'lowerarm_twist_02_r',
         'upperarm_twist_01_r', 'upperarm_twist_02_r')

SHOTS = [(clip, t / 1000.0) for clip, times in (
    ('HeavyCharge', (0, 120, 200, 350, 500, 650, 1000, 1400, 2000)),
    ('HeavyRelease', (75, 400, 800)),
) for t in times]

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']

left = arms.copy()
left.data = arms.data.copy()
left.modifiers.clear()
modifier = left.modifiers.new('Armature', 'ARMATURE')
modifier.object = rig
left.parent = rig
scene.collection.objects.link(left)

groups = {g.name: g.index for g in left.vertex_groups}
right_indices = [groups[n] for n in RIGHT if n in groups]
moved = 0
for vertex in left.data.vertices:
    weight = sum(g.weight for g in vertex.groups if g.group in right_indices)
    if weight > .5:
        vertex.co += Vector((0, 0, 12))
        moved += 1
left.data.update()
print('moved right-side vertices:', moved, flush=True)

for ob in scene.objects:
    keep = ob in (rig, left)
    ob.hide_render = not keep
    try:
        ob.hide_set(not keep)
    except RuntimeError:
        pass

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('LeftOnlyWorld')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .20, .24, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = .8

clay = bpy.data.materials.new('LeftOnlyClay')
clay.use_nodes = True
bsdf = clay.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.60, .63, .68, 1)
bsdf.inputs['Roughness'].default_value = .60
left.data.materials.clear()
left.data.materials.append(clay)
for poly in left.data.polygons:
    poly.material_index = 0

for name, loc, energy, size in [('Key', (-.5, -.4, 1.1), 110, 1.3),
                                ('Fill', (.6, .5, .5), 60, 1.2),
                                ('Rim', (-.3, 1.0, .3), 80, .9)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.shape = 'DISK'
    light.size = size
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((-.2, .1, -.2)) - ob.location).to_track_quat('-Z', 'Y').to_euler()

data = bpy.data.cameras.new('LeftOnlyCamera')
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


VIEWS = {
    'front': Vector((0.0, -1.4, 0.25)),
    'back': Vector((0.2, 1.4, 0.35)),
    'outside': Vector((-1.5, -0.3, 0.15)),
    'top': Vector((-0.2, -0.2, 1.5)),
}

for clip, seconds in SHOTS:
    activate(clip, seconds)
    tag = '%s_%03dms' % (clip, round(seconds * 1000))
    A, E, H = [rig.pose.bones[n].matrix.translation
               for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
    centre = (A + E + H) / 3
    span = max((A - H).length, .45) * 1.25
    for view, offset in VIEWS.items():
        camera.location = centre + offset.normalized() * span * 2.1
        camera.rotation_euler = (centre - camera.location).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'ORTHO'
        data.ortho_scale = span * 2.0
        scene.render.filepath = str(OUT / ('%s_%s.png' % (tag, view)))
        bpy.ops.render.render(write_still=True)
    print('SHOT', tag, flush=True)

print('RENDER_LEFT_ONLY_DONE', flush=True)
