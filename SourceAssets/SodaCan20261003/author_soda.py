"""Retain the Fab can's geometry/UVs and author a centimeter gameplay mesh."""
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent
SOURCE = Path('D:/FPS3D/VaultCache/FabLibrary/Soda_Can-685c71b6/fbx')
SOURCE_FBX = SOURCE / 'soda-can_extracted/source/SODA_extracted/SODA_4K.fbx'
SOURCE_TEXTURES = SOURCE / 'soda-can_extracted/textures'
EXPORT = OUT / 'Export'
EXPORT.mkdir(exist_ok=True)
HEIGHT_CM = 12.2

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SOURCE_FBX))
parts = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
         and not obj.name.startswith(('UCX_', 'UBX_'))]
source_objects = [obj.name for obj in parts]
if not parts:
    raise RuntimeError('The downloaded FBX contains no can mesh.')
# Bake the imported hierarchy before joining, keeping every original mesh part.
for part in parts:
    world = part.matrix_world.copy()
    part.data = part.data.copy()
    part.data.transform(world)
    part.parent = None
    part.matrix_parent_inverse = Matrix.Identity(4)
    part.matrix_world = Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT')
for part in parts:
    part.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
if len(parts) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
points = [vertex.co.copy() for vertex in obj.data.vertices]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
extent = high - low
axis_index = max(range(3), key=lambda i: extent[i])
axis = Vector(tuple(float(i == axis_index) for i in range(3)))
rotation = axis.rotation_difference(Vector((0, 0, 1))).to_matrix().to_4x4()
transform = Matrix.Translation((0, 0, HEIGHT_CM / 200)) @ Matrix.Scale(
    (HEIGHT_CM / 100) / extent[axis_index], 4) @ rotation @ Matrix.Translation(-(low + high) * .5)
obj.data.transform(transform)
obj.name = 'SM_SodaCan'
obj.data.update()
for other in list(bpy.context.scene.objects):
    if other != obj:
        bpy.data.objects.remove(other, do_unlink=True)

material = bpy.data.materials.new('M_SodaCan')
material.use_nodes = True
surface = material.node_tree.nodes.get('Principled BSDF')
textures = {}
for name, filename, socket in (
    ('BaseColor', 'Color_4k.png', 'Base Color'),
    ('Roughness', 'Roughness_4k.png', 'Roughness'),
    ('Metalness', 'Metalness_4k.png', 'Metallic'),
):
    path = SOURCE_TEXTURES / filename
    node = material.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = bpy.data.images.load(str(path))
    if name != 'BaseColor':
        node.image.colorspace_settings.name = 'Non-Color'
    node.image.pack()
    material.node_tree.links.new(node.outputs['Color'], surface.inputs[socket])
    textures[name] = str(path)
obj.data.materials.clear()
obj.data.materials.append(material)
for polygon in obj.data.polygons:
    polygon.material_index = 0
obj.data.calc_loop_triangles()
triangles = len(obj.data.loop_triangles)

bpy.context.view_layer.update()
points = [Vector(p) for p in obj.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
dimensions = high - low
# A simple convex cylinder travels with the can if a mesh physics user needs it.
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=max(dimensions.x, dimensions.y) * .5,
    depth=dimensions.z, location=(low + high) * .5)
collision = bpy.context.object
collision.name = 'UCX_SM_SodaCan_00'
collision.scale.x = dimensions.x / max(dimensions.x, dimensions.y)
collision.scale.y = dimensions.y / max(dimensions.x, dimensions.y)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
collision.select_set(True)
bpy.context.view_layer.objects.active = obj
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
for part in (obj, collision):
    part.data.transform(Matrix.Scale(100, 4))
    part.location *= 100
fbx = EXPORT / 'SM_SodaCan.fbx'
try:
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
        global_scale=1, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Y', axis_up='Z', bake_space_transform=True,
        mesh_smooth_type='FACE', use_mesh_modifiers=True, path_mode='STRIP')
finally:
    for part in (obj, collision):
        part.data.transform(Matrix.Scale(.01, 4))
        part.location *= .01
    scene.unit_settings.scale_length = 1
bpy.data.objects.remove(collision, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'SodaCan_Authored.blend'))
manifest = {
    'listing': 'https://www.fab.com/listings/685c71b6-e33d-4262-9149-0a01787e0d85',
    'publisher': 'Dkalq Studio', 'source_mesh': str(SOURCE_FBX),
    'source_metadata': str(SOURCE / 'metadata'), 'source_objects': source_objects,
    'mesh': str(fbx), 'triangles': triangles, 'dimensions_cm': [v * 100 for v in dimensions],
    'grip_height_cm': HEIGHT_CM / 2, 'source_length_axis': axis_index,
    'export_units': 'centimeters; baked geometry and identity object transform; bottom origin',
    'textures': textures, 'icon': 'D:/FPS3D/FPSGAME/Content/ColdSteelData/Icons/soda_can.png',
    'icon_size': [320, 320], 'runtime_tested': False,
}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('SODA_CAN_AUTHORED triangles=' + str(triangles) + ' dimensions_cm=' +
      str(manifest['dimensions_cm']) + ' source_objects=' + str(source_objects))
