"""User-requested previews of the completed asset; no UE import or model edits."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Preview'
OUT.mkdir(exist_ok=True)
TEXTURES = ROOT.parent / 'RSH12Integration20261003/Original/Extracted/textures'
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'RSH12_CubeSuppressor_Long_FitSource.blend'))
scene = bpy.context.scene
main = bpy.data.objects['SM_RSH12_CubeSuppressor_Long']
main.hide_set(False)
main.hide_render = False
refs_collection = bpy.data.collections['REFERENCE_RSH_Static_DoNotExport']
refs_collection.hide_render = False
refs_collection.hide_viewport = False
refs = [o for o in refs_collection.all_objects if o.type == 'MESH']
for o in refs:
    o.hide_render = False
    o.hide_set(False)
for name in ['EDITABLE_ExteriorParts', 'EDITABLE_ReliefCutters', 'INTERFACE_Guides']:
    bpy.data.collections[name].hide_render = True
bpy.data.objects['SM_RSH12_CubeSuppressor_Long_LOD1'].hide_render = True

# The existing source gun uses its own original UVs and PBR images in this preview.
mat = bpy.data.materials.new('PREVIEW_Original_RSH_PBR')
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
output = nodes.new('ShaderNodeOutputMaterial')
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
for suffix, socket, color_space in [
    ('albedo.jpg', 'Base Color', 'sRGB'),
    ('roughness.jpg', 'Roughness', 'Non-Color'),
    ('metallic.jpg', 'Metallic', 'Non-Color'),
]:
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(TEXTURES / ('DefaultMaterial_' + suffix)), check_existing=True)
    tex.image.colorspace_settings.name = color_space
    links.new(tex.outputs['Color'], bsdf.inputs[socket])
normal_tex = nodes.new('ShaderNodeTexImage')
normal_tex.image = bpy.data.images.load(str(TEXTURES / 'DefaultMaterial_normal.png'), check_existing=True)
normal_tex.image.colorspace_settings.name = 'Non-Color'
normal = nodes.new('ShaderNodeNormalMap')
normal.inputs['Strength'].default_value = 1.0
links.new(normal_tex.outputs['Color'], normal.inputs['Color'])
links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
for o in refs:
    o.data.materials.clear()
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.material_index = 0

stage = bpy.data.collections.new('PREVIEW_Studio')
scene.collection.children.link(stage)
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = 0
world = bpy.data.worlds.new('PREVIEW_StudioWorld')
world.use_nodes = True
world.node_tree.nodes.clear()
background = world.node_tree.nodes.new('ShaderNodeBackground')
world_output = world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(background.outputs['Background'], world_output.inputs['Surface'])
background.inputs['Color'].default_value = (.27, .28, .30, 1)
background.inputs['Strength'].default_value = .5
scene.world = world

camera_data = bpy.data.cameras.new('PREVIEW_Camera')
camera = bpy.data.objects.new('PREVIEW_Camera', camera_data)
stage.objects.link(camera)
camera_data.type = 'ORTHO'
camera_data.clip_start = .001
camera_data.clip_end = 100
scene.camera = camera

bpy.ops.mesh.primitive_plane_add(size=200)
floor = bpy.context.object
floor.name = 'PREVIEW_StudioFloor'
for collection in list(floor.users_collection):
    collection.objects.unlink(floor)
stage.objects.link(floor)
floor_mat = bpy.data.materials.new('PREVIEW_FloorGrey')
floor_mat.use_nodes = True
floor_mat.node_tree.nodes.clear()
floor_bsdf = floor_mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
floor_output = floor_mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
floor_mat.node_tree.links.new(floor_bsdf.outputs['BSDF'], floor_output.inputs['Surface'])
floor_bsdf.inputs['Base Color'].default_value = (.15, .16, .175, 1)
floor_bsdf.inputs['Roughness'].default_value = .8
floor.data.materials.append(floor_mat)

light_specs = [
    ((.08, .28, .5), 45, .4),
    ((-.28, .18, .14), 20, .3),
    ((0, -.3, .3), 60, .32),
    ((.3, .0, .15), 20, .25),
]
lights = []
for index, (_, energy, size) in enumerate(light_specs):
    data = bpy.data.lights.new(f'PREVIEW_Area_{index}', 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    light = bpy.data.objects.new(data.name, data)
    stage.objects.link(light)
    lights.append(light)


def corners(objects):
    return [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]


def render_view(name, objects, direction, resolution):
    scene.render.resolution_x, scene.render.resolution_y = resolution
    bpy.context.view_layer.update()
    points = corners(objects)
    low = Vector(tuple(min(p[k] for p in points) for k in range(3)))
    high = Vector(tuple(max(p[k] for p in points) for k in range(3)))
    target = (low + high) * .5
    span = max(high - low)
    direction = Vector(direction).normalized()
    rotation = (-direction).to_track_quat('-Z', 'Y')
    right = rotation @ Vector((1, 0, 0))
    up = rotation @ Vector((0, 1, 0))
    projected_x = [(p - target).dot(right) for p in points]
    projected_y = [(p - target).dot(up) for p in points]
    target += right * ((min(projected_x) + max(projected_x)) * .5)
    target += up * ((min(projected_y) + max(projected_y)) * .5)
    camera.location = target + direction * (span * 3)
    camera.rotation_euler = rotation.to_euler()
    aspect = resolution[0] / resolution[1]
    camera_data.ortho_scale = max(max(projected_x) - min(projected_x),
                                 (max(projected_y) - min(projected_y)) * aspect) * 1.18
    floor.location.z = low.z - .0015
    scale = span / .53
    for light, (offset, energy, size) in zip(lights, light_specs):
        light.location = target + Vector(offset) * scale
        light.rotation_euler = (target - light.location).to_track_quat('-Z', 'Y').to_euler()
        light.data.energy = energy * scale * scale * .08
        light.data.size = size * scale
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (name + '.blend')))
    print('PREVIEW_RENDER_START', name, flush=True)
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_RENDER_SAVED', scene.render.filepath, flush=True)


bpy.ops.file.pack_all()
render_view('RSH12_Cube_Long_Mounted', [main] + refs, (.28, 1, .23), (1800, 1100))
refs_collection.hide_render = True
refs_collection.hide_viewport = True
render_view('RSH12_Cube_Long_Detail', [main], (.5, 1, .38), (1600, 1000))
(OUT / 'preview_receipt.json').write_text(json.dumps({
    'source': str(ROOT / 'RSH12_CubeSuppressor_Long_FitSource.blend'),
    'renderer': 'Blender Cycles',
    'scope': 'User requested actual completed model preview',
    'images': ['RSH12_Cube_Long_Mounted.png', 'RSH12_Cube_Long_Detail.png'],
    'ue_imported': False,
    'gameplay_tested': False,
    'asset_geometry_changed': False,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('RSH_CUBE_PREVIEWS_COMPLETE', flush=True)
