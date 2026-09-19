"""Editable Blender source and production UI icon from the actual Vibe3D FBX.

The material graph mirrors the existing UE ASH coat. This is a required UI
asset, not a gameplay/acceptance render. No image-generation stand-in is used.
"""
import json
from pathlib import Path
import bpy
from mathutils import Vector

O = Path(__file__).resolve().parent
T = O.parent/'ASH12UniversalAttachments20260919/Textures'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.
bpy.ops.import_scene.fbx(filepath=str(O/'SM_ASH12_TacticalBrake.fbx'))
models = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']


def coating(name, colour, roughness, metal, uv_names):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*colour, 1)
    bsdf.inputs['Metallic'].default_value = metal
    # ORM is mapped using the existing coat's independent physical UV3.
    uv3 = nodes.new('ShaderNodeUVMap'); uv3.uv_map = uv_names[3]
    packed = nodes.new('ShaderNodeTexImage')
    packed.image = bpy.data.images.load(str(T/'T_ASH12_AttachmentCoat_ORM.png'), check_existing=True)
    packed.image.colorspace_settings.name = 'Non-Color'
    split = nodes.new('ShaderNodeSeparateColor')
    links.new(uv3.outputs['UV'], packed.inputs['Vector'])
    links.new(packed.outputs['Color'], split.inputs['Color'])
    offset = nodes.new('ShaderNodeMath'); offset.operation = 'ADD'
    offset.inputs[1].default_value = roughness-.45
    links.new(split.outputs['Green'], offset.inputs[0])
    links.new(offset.outputs[0], bsdf.inputs['Roughness'])
    # Tangent normal remains UV0 at the same 12x detail tiling. Convert the
    # texture's DirectX green channel for Blender's OpenGL normal convention.
    uv0 = nodes.new('ShaderNodeUVMap'); uv0.uv_map = uv_names[0]
    scale = nodes.new('ShaderNodeVectorMath'); scale.operation = 'SCALE'
    scale.inputs['Scale'].default_value = 12.
    links.new(uv0.outputs['UV'], scale.inputs[0])
    normal_tex = nodes.new('ShaderNodeTexImage')
    normal_tex.image = bpy.data.images.load(str(T/'T_ASH12_AttachmentCoat_NormalDX.png'), check_existing=True)
    normal_tex.image.colorspace_settings.name = 'Non-Color'
    links.new(scale.outputs['Vector'], normal_tex.inputs['Vector'])
    channels = nodes.new('ShaderNodeSeparateColor')
    links.new(normal_tex.outputs['Color'], channels.inputs['Color'])
    invert = nodes.new('ShaderNodeMath'); invert.operation = 'SUBTRACT'; invert.inputs[0].default_value = 1.
    links.new(channels.outputs['Green'], invert.inputs[1])
    rgb = nodes.new('ShaderNodeCombineColor')
    links.new(channels.outputs['Red'], rgb.inputs['Red'])
    links.new(invert.outputs[0], rgb.inputs['Green'])
    links.new(channels.outputs['Blue'], rgb.inputs['Blue'])
    normal = nodes.new('ShaderNodeNormalMap'); normal.uv_map = uv_names[0]
    links.new(rgb.outputs['Color'], normal.inputs['Color'])
    links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


for obj in models:
    uvs = [layer.name for layer in obj.data.uv_layers]
    mats = [coating('ASH_BlackMetal_Shell', (.090, .095, .103), .45, .70, uvs),
            coating('ASH_BlackMetal_Mount', (.065, .068, .072), .50, .65, uvs)]
    obj.data.materials.clear()
    for mat in mats: obj.data.materials.append(mat)
    obj['Source'] = 'Current editor Vibe3D author_vibe.py; native UE FBX export'
    obj['MountFrame'] = '+X forward / +Z up, rear contact at X=0'

scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('Neutral_UI_World')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.12, .12, .12, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
center = Vector((.042, 0, 0))
camera_data = bpy.data.cameras.new('AttachmentIconCamera')
camera = bpy.data.objects.new('AttachmentIconCamera', camera_data)
scene.collection.objects.link(camera)
camera.location = center+Vector((0, .7, 0))
camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'; camera_data.ortho_scale = .084/.83
scene.camera = camera
for index, (location, energy, size) in enumerate([
        ((.12, .26, .35), 18, .35), ((0, -.18, .15), 12, .25), ((.35, .10, -.12), 7, .22)]):
    light = bpy.data.lights.new('NeutralIconArea'+str(index), 'AREA')
    light.energy = energy; light.shape = 'DISK'; light.size = size; light.color = (1, 1, 1)
    obj = bpy.data.objects.new(light.name, light); scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (center-obj.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = str(O/'ue_ash12_muzzle_ash12_tactical_brake.png')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ASH12_TacticalBrake_Editable.blend'))
bpy.ops.render.render(write_still=True)
(O/'icon.json').write_text(json.dumps({
    'png': scene.render.filepath, 'source': 'SM_ASH12_TacticalBrake.fbx',
    'camera': 'orthographic side, forward to screen left, +Z up',
    'size': [1024, 1024], 'background': 'transparent',
    'materials': 'actual ASH dry black coat parameters and textures, neutral white light',
    'purpose': 'production gunsmith UI icon', 'tested': False}, indent=2), encoding='utf-8')
print('ASH12_BRAKE_ICON_CREATED')
