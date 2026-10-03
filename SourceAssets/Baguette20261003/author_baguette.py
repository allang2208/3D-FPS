"""Retain the downloaded Quixel geometry and produce its inventory icon."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent
SOURCE = Path('D:/FPS3D/VaultCache/FabLibrary/Baguette_Bread-e555b990/fbx/high/baguette_bread_ujqhebs_h_extracted')
EXPORT = OUT / 'Export'
EXPORT.mkdir(exist_ok=True)
ICON = Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/Icons/baguette_bread.png')
LENGTH_CM = 30.0
HALF_LENGTH_M = LENGTH_CM / 200.0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SOURCE / 'Baguette_Bread_ujqhebs_High.fbx'))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and not obj.name.startswith(('UCX_', 'UBX_'))]
obj = max(meshes, key=lambda m: len(m.data.polygons))
source_name = obj.name
obj.data = obj.data.copy()
world = obj.matrix_world.copy()
points = [world @ v.co for v in obj.data.vertices]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
extent = high - low
length_axis = max(range(3), key=lambda i: extent[i])
axis = Vector(tuple(float(i == length_axis) for i in range(3)))
rotation = axis.rotation_difference(Vector((0, 0, 1))).to_matrix().to_4x4()
transform = Matrix.Scale((LENGTH_CM / 100) / extent[length_axis], 4) @ rotation @ Matrix.Translation(-(low + high) * .5) @ world
obj.data.transform(transform)
# The Quixel FBX parent carries a scale/axis transform. Clear it before deleting
# the import hierarchy, or its inverse becomes a second transform on the loaf.
obj.parent = None
obj.matrix_parent_inverse = Matrix.Identity(4)
obj.matrix_world = Matrix.Identity(4)
# The bottom origin and center grip share the same authored length.
for vertex in obj.data.vertices:
    vertex.co.z += HALF_LENGTH_M
obj.name = 'SM_Baguette'
obj.data.update()
for other in list(bpy.context.scene.objects):
    if other != obj:
        bpy.data.objects.remove(other, do_unlink=True)

mat = bpy.data.materials.new('Bread')
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
surface = nodes.get('Principled BSDF')
surface.inputs['Metallic'].default_value = 0
surface.inputs['Roughness'].default_value = .7
textures = {}
for name, input_name in (('BaseColor', 'Base Color'), ('Roughness', 'Roughness')):
    path = SOURCE / ('Baguette_Bread_ujqhebs_High_4K_' + name + '.jpg')
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(path))
    tex.image.pack()
    if name != 'BaseColor':
        tex.image.colorspace_settings.name = 'Non-Color'
    links.new(tex.outputs['Color'], surface.inputs[input_name])
    textures[name] = str(path)
normal_path = SOURCE / 'Baguette_Bread_ujqhebs_High_4K_Normal.jpg'
normal_tex = nodes.new('ShaderNodeTexImage')
normal_tex.image = bpy.data.images.load(str(normal_path))
normal_tex.image.colorspace_settings.name = 'Non-Color'
normal_tex.image.pack()
separate = nodes.new('ShaderNodeSeparateColor')
combine = nodes.new('ShaderNodeCombineColor')
invert = nodes.new('ShaderNodeMath')
invert.operation = 'SUBTRACT'
invert.inputs[0].default_value = 1
links.new(normal_tex.outputs['Color'], separate.inputs['Color'])
links.new(separate.outputs['Red'], combine.inputs['Red'])
links.new(separate.outputs['Green'], invert.inputs[1])
links.new(invert.outputs[0], combine.inputs['Green'])
links.new(separate.outputs['Blue'], combine.inputs['Blue'])
normal = nodes.new('ShaderNodeNormalMap')
links.new(combine.outputs['Color'], normal.inputs['Color'])
links.new(normal.outputs['Normal'], surface.inputs['Normal'])
textures['Normal'] = str(normal_path)
for name in ('AO', 'Specular'):
    textures[name] = str(SOURCE / ('Baguette_Bread_ujqhebs_High_4K_' + name + '.jpg'))
obj.data.materials.clear()
obj.data.materials.append(mat)
obj.data.calc_loop_triangles()
triangles = len(obj.data.loop_triangles)

bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.context.view_layer.update()
points = [Vector(v) for v in obj.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
bpy.ops.mesh.primitive_cube_add(size=1, location=(low + high) * .5)
collision = bpy.context.object
collision.name = 'UCX_SM_Baguette_00'
collision.dimensions = high - low
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
collision.select_set(True)
bpy.context.view_layer.objects.active = obj
fbx = EXPORT / 'SM_Baguette.fbx'
# Export actual centimeter coordinates with no residual object scale. Keep the
# editable/render scene in meters, and restore it even if the export fails.
for part in (obj, collision):
    part.data.transform(Matrix.Scale(100, 4))
    part.location *= 100
bpy.context.scene.unit_settings.scale_length = .01
try:
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
        global_scale=1, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Y', axis_up='Z', bake_space_transform=True,
        mesh_smooth_type='FACE', use_mesh_modifiers=True, path_mode='STRIP')
finally:
    for part in (obj, collision):
        part.data.transform(Matrix.Scale(.01, 4))
        part.location *= .01
    bpy.context.scene.unit_settings.scale_length = 1
bpy.data.objects.remove(collision, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.cycles.device = 'CPU'
scene.render.resolution_x = 320
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = True
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = -.4
scene.world = bpy.data.worlds.new('BaguetteIconStudio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.72, .75, .78, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .12
def aim(actor, target):
    actor.rotation_euler = (Vector(target) - actor.location).to_track_quat('-Z', 'Y').to_euler()
def light(name, position, power, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'RECTANGLE'
    data.size = size
    data.size_y = .6
    actor = bpy.data.objects.new(name, data)
    scene.collection.objects.link(actor)
    actor.location = position
    aim(actor, (0, 0, HALF_LENGTH_M))
light('SoftKey', (.40, -.45, .45), 8, .32)
light('SoftFill', (-.32, -.22, .25), 3, .32)
light('Edge', (.18, .34, .34), 5, .18)
camera = bpy.data.objects.new('BaguetteInventoryCamera', bpy.data.cameras.new('BaguetteInventoryCamera'))
scene.collection.objects.link(camera)
camera.location = (.7, -.18, HALF_LENGTH_M)
camera.data.type = 'ORTHO'
aim(camera, (0, 0, HALF_LENGTH_M))
bpy.context.view_layer.update()
# Fit the real silhouette in this 1x3 canvas. Its full length stays visible,
# while the crust's broad side faces the camera without a baked frame or text.
view = camera.matrix_world.inverted()
projected = [view @ (obj.matrix_world @ v.co) for v in obj.data.vertices]
width = max(v.x for v in projected) - min(v.x for v in projected)
height = max(v.y for v in projected) - min(v.y for v in projected)
camera.data.ortho_scale = max(height / .90, width * 3 / .86)
scene.camera = camera
scene.render.filepath = str(ICON)
# This render is the requested inventory texture, not a gameplay preview.
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Baguette_Authored.blend'))
receipt = {'source': str(SOURCE), 'source_mesh': source_name,
    'listing': 'https://www.fab.com/listings/e555b990-d7ca-49db-bdde-653ce637854e',
    'publisher': 'Quixel Megascans', 'mesh': str(fbx), 'triangles': triangles,
    'length_cm': LENGTH_CM, 'grip_height_cm': LENGTH_CM / 2, 'dimensions_m': list(high - low),
    'export_units': 'centimeters; baked geometry and identity parent/object transform',
    'textures': textures, 'icon': str(ICON), 'icon_size': [320, 960],
    'normal_map_assumption': 'Quixel Unreal/DirectX; green inverted for Blender icon only',
    'runtime_tested': False}
(OUT / 'manifest.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('BAGUETTE_SOURCE_SAVED ' + str(triangles))
