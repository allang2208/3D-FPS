"""Produce the three deployed attachment icons from the delivered PBR meshes."""
import bpy, json
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P / 'RuneSword_Pommels_PBR.blend'))
rows = json.loads((P / 'model_exports.json').read_text(encoding='utf-8'))
out = P / 'Icons'
out.mkdir(exist_ok=True)
scene = bpy.data.scenes.new('RunePommel_AttachmentIcons')
bpy.context.window.scene = scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('PommelIcon_Studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes.clear()
background = scene.world.node_tree.nodes.new('ShaderNodeBackground')
background.inputs['Color'].default_value = (.28, .28, .28, 1)
background.inputs['Strength'].default_value = .45
world_output = scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(background.outputs[0], world_output.inputs['Surface'])
camdata = bpy.data.cameras.new('PommelIcon_Orthographic')
camera = bpy.data.objects.new('PommelIcon_Orthographic', camdata)
scene.collection.objects.link(camera)
scene.camera = camera
camdata.type = 'ORTHO'
lights = []
for name, offset, power, size in [
    ('Key', (-2, -3, 3), 850, 2.4),
    ('Fill', (2.5, -1.5, .7), 550, 2),
    ('Rim', (.5, 2.5, 2), 1100, 1.8),
]:
    data = bpy.data.lights.new('PommelIcon_' + name, 'AREA')
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    lights.append((obj, Vector(offset), power, size))
ids = {'meteor': 'ballast_hardened', 'jade_core': 'ballast_rune', 'swift': 'ballast_magic_orb'}
receipt = []
for row in rows:
    source = bpy.data.objects[row['mesh']]
    model = source.copy()
    model.name = 'Icon_' + row['mesh']
    scene.collection.objects.link(model)
    model.hide_set(False)
    model.hide_render = False
    points = [model.matrix_world @ Vector(p) for p in model.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) / 2
    span = max(high.x - low.x, high.z - low.z)
    camera.location = center + Vector((0, -4 * span, 0))
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camdata.ortho_scale = span / .83
    camdata.clip_start = .001
    for obj, offset, power, size in lights:
        obj.location = center + offset * span
        obj.rotation_euler = (center - obj.location).to_track_quat('-Z', 'Y').to_euler()
        obj.data.energy = power * span * span
        obj.data.size = size * span
    file = out / ('ue_rune_sword_pommel_' + ids[row['id']] + '.png')
    scene.render.filepath = str(file)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    receipt.append({'id': ids[row['id']], 'weapon': 'ue_rune_sword', 'model': row['mesh'],
                    'source_blend': str(P / 'RuneSword_Pommels_PBR.blend'), 'source_object': row['mesh'],
                    'image': str(file), 'resolution': [1024, 1024], 'rgba': True,
                    'mount_axis': '+Z toward blade; pommel body extends -Z',
                    'view': '-Y, level orthographic front', 'frame_fill': .83,
                    'material_note': 'Delivered PBR; Blender crystal transmission approximates UE translucent material.'})
    model.hide_render = True
    model.hide_set(True)
    print('POMMEL_ICON_RENDERED', file)
first = bpy.data.objects['Icon_' + rows[-1]['mesh']]
first.hide_set(False)
first.hide_render = False
# Retain the authoring cameras and lighting without changing the model master.
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'RuneSword_Pommel_Icons.blend'))
(P / 'icon_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
