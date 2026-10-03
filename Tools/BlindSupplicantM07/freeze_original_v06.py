"""Create an editable master directly from the user GLB source accessors.

Production only: no rig substitution, cutting, render, simulation or engine run.
"""
import json
from pathlib import Path
import bpy
import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryOriginalV06'
OUT.mkdir(parents=True, exist_ok=True)
source = np.load(ROOT/'Authoring/source_mesh.npz')
raw = source['positions']
tri = source['indices'].reshape(-1, 3).astype(np.int32)
scale = 310.0 / float(raw[:, 1].max() - raw[:, 1].min())
ground = float(raw[:, 1].min())
points = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1]-ground] * scale
normals = source['normals']
normals = np.c_[normals[:, 0], -normals[:, 2], normals[:, 1]]
uv = source['uvs'].copy()
uv[:, 1] = 1.0-uv[:, 1]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
mesh = bpy.data.meshes.new('M07_Original_AllSourceFaces')
mesh.vertices.add(len(points))
mesh.vertices.foreach_set('co', points.astype(np.float32).ravel())
mesh.loops.add(tri.size)
mesh.loops.foreach_set('vertex_index', tri.ravel())
mesh.polygons.add(len(tri))
mesh.polygons.foreach_set('loop_start', np.arange(len(tri), dtype=np.int32)*3)
mesh.polygons.foreach_set('loop_total', np.full(len(tri), 3, dtype=np.int32))
mesh.polygons.foreach_set('use_smooth', np.ones(len(tri), dtype=bool))
mesh.update()
layer = mesh.uv_layers.new(name='UVMap')
layer.data.foreach_set('uv', uv[tri.ravel()].astype(np.float32).ravel())
# Smooth flags precede custom normals, preserving the original loop shading.
mesh.normals_split_custom_set_from_vertices(normals.tolist())
mesh.attributes.new(name='source_vertex_id', type='INT', domain='POINT').data.foreach_set(
    'value', np.arange(len(points), dtype=np.int32))
mesh.attributes.new(name='source_face_id', type='INT', domain='FACE').data.foreach_set(
    'value', np.arange(len(tri), dtype=np.int32))
obj = bpy.data.objects.new('M07_Original_Frozen_Source', mesh)
scene.collection.objects.link(obj)
obj['input_source'] = str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb')
obj['source_surface_replaced'] = False
obj['source_coordinates_conversion'] = '(X,-Z,Y-ground) * scale_cm; identity object'
material = bpy.data.materials.new('M07_OriginalOpaquePBR')
material.use_nodes = True
material.use_backface_culling = False
nodes = material.node_tree.nodes
links = material.node_tree.links
shader = nodes.get('Principled BSDF')
for filename, socket, data in [
    ('M07_basecolor_source.jpg', 'Base Color', False),
    ('M07_roughness.png', 'Roughness', True),
    ('M07_metallic.png', 'Metallic', True),
]:
    image = bpy.data.images.load(str(ROOT/'Textures'/filename), check_existing=True)
    if data:
        image.colorspace_settings.name = 'Non-Color'
    node = nodes.new('ShaderNodeTexImage')
    node.image = image
    links.new(node.outputs['Color'], shader.inputs[socket])
normal = nodes.new('ShaderNodeTexImage')
normal.image = bpy.data.images.load(str(ROOT/'Textures/M07_normal_source.jpg'), check_existing=True)
normal.image.colorspace_settings.name = 'Non-Color'
normal_map = nodes.new('ShaderNodeNormalMap')
links.new(normal.outputs['Color'], normal_map.inputs['Color'])
links.new(normal_map.outputs['Normal'], shader.inputs['Normal'])
mesh.materials.append(material)
scene['m07_revision'] = 'OriginalV06 untouched source surface in centimeter authoring frame'
scene['m07_tested'] = False
destination = OUT/'M07_Original_Unmodified_V06.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
record = {
    'stage': 'original editable source restored; partition, rig and cloth are separate production',
    'source': obj['input_source'],
    'original_sha256': '06acb6cf86a78ed3c53a1150cff77ba05636c1ea56cfc3b3044e92b70f0e69bc',
    'saved_blend': str(destination), 'source_vertices': len(points),
    'source_triangles': len(tri), 'original_surface_replaced': False,
    'original_uv_retained': True, 'original_pbr_retained': True,
    'source_vertex_and_face_ids_authored': True,
    'reference_space': 'centimeters, identity object, scene unit 0.01',
    'scale_cm': scale, 'ground_source_y': ground, 'target_height_cm': 310,
    'rigged': False, 'ue_imported': False, 'tested': False, 'user_accepted': False,
}
(OUT/'original_source_delivery.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(record, ensure_ascii=False), flush=True)
