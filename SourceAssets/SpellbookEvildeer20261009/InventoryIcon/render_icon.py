"""Render the selected production book for the shared equipment/inventory icon.

Blender background entry. Reads the catalog's display orientation and footprint;
saves an independent author scene and the actual transparent catalog PNG.
Does not export or modify the held mesh, grip, animation, or UE assets.
"""
import json
import math
import shutil
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent
PROJECT = SOURCE.parent.parent
DEFINITION = 'ue_alchemy_spellbook'
FILL = 0.91
catalog = json.loads((PROJECT / 'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
item = catalog[DEFINITION]
width, height = round(320 * item['grid_w'] / item['grid_h']), 320
final = PROJECT / 'Content/ColdSteelData' / item['ue_icon']
final.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'Spellbook_Alchemy.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
book = bpy.data.objects['SM_Spellbook_Alchemy_Closed']
for obj in list(bpy.data.objects):
    if obj != book:
        bpy.data.objects.remove(obj, do_unlink=True)
for collection in bpy.data.collections:
    collection.hide_render = False
    collection.hide_viewport = False
book.hide_render = False
book.hide_viewport = False
book.hide_set(False)
book.data = book.data.copy()
book.data.transform(Matrix.Scale(0.01, 4))
book.matrix_world = Matrix.Identity(4)
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

# UE FRotator: yaw about +Z, pitch about -Y, roll about -X.
# Capture looks along UE +X with screen right +Y and up +Z.
pitch, yaw, roll = [math.radians(item[key]) for key in ('ue_icon_pitch', 'ue_icon_yaw', 'ue_icon_roll')]
orient = (Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-pitch, 3, 'Y')
          @ Matrix.Rotation(-roll, 3, 'X'))
ue_to_blender = Matrix.Diagonal(Vector((1, -1, 1)))
right = ue_to_blender @ (orient.transposed() @ Vector((0, 1, 0)))
up = ue_to_blender @ (orient.transposed() @ Vector((0, 0, 1)))
normal = right.cross(up).normalized()
points = [book.matrix_world @ vertex.co for vertex in book.data.vertices]
xs = [point.dot(right) for point in points]
ys = [point.dot(up) for point in points]
zs = [point.dot(normal) for point in points]
center = (right * ((min(xs) + max(xs)) / 2) + up * ((min(ys) + max(ys)) / 2)
          + normal * ((min(zs) + max(zs)) / 2))
span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
camera_data = bpy.data.cameras.new('BookIconCamera')
camera_data.type = 'ORTHO'
camera_data.ortho_scale = max(span_y, span_x * height / width) / FILL
camera_data.clip_start, camera_data.clip_end = 0.01, 10
camera = bpy.data.objects.new('BookIconCamera', camera_data)
scene.collection.objects.link(camera)
camera.location = center + normal * 0.8
camera.rotation_euler = Matrix((right, up, normal)).transposed().to_euler()
scene.camera = camera

for name, offset, power, size in (
    ('Key', (-0.38, 0.42, 0.58), 35, 0.5),
    ('Fill', (0.4, 0.08, 0.45), 12, 0.45),
    ('TopRim', (0.05, 0.45, -0.1), 18, 0.3),
):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size = power, 'DISK', size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = center + right * offset[0] + up * offset[1] + normal * offset[2]
    light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()

scene.world = bpy.data.worlds.new('BookIconStudio')
scene.world.use_nodes = True
scene.world.node_tree.nodes.clear()
background = scene.world.node_tree.nodes.new('ShaderNodeBackground')
world_output = scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(background.outputs['Background'], world_output.inputs['Surface'])
background.inputs['Color'].default_value = (0.3, 0.32, 0.4, 1)
background.inputs['Strength'].default_value = 0.25
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = -0.5
scene.render.filepath = str(OUT / (DEFINITION + '.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Spellbook_InventoryIcon.blend'))
bpy.ops.render.render(write_still=True)
shutil.copy2(scene.render.filepath, final)
(OUT / 'production.json').write_text(json.dumps({
    'definition': DEFINITION,
    'source': str(SOURCE / 'Spellbook_Alchemy.blend'),
    'object': book.name,
    'materials': [slot.material.name for slot in book.material_slots],
    'runtime_orientation': {key: item[key] for key in ('ue_icon_pitch', 'ue_icon_yaw', 'ue_icon_roll')},
    'size': [width, height],
    'grid': [item['grid_w'], item['grid_h']],
    'fill': FILL,
    'projection': 'orthographic',
    'background': 'transparent',
    'author_png': scene.render.filepath,
    'catalog_png': str(final),
    'game_testing_performed': False,
}, indent=2), encoding='utf-8')
print('SPELLBOOK_ICON_SAVED ' + str(final))
