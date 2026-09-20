"""Prepare the user supplied Meshy pickaxe, preserving its UVs and PBR images.

Production exports only. No preview rendering or runtime tests.
"""
import hashlib
import json
import shutil
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
SOURCE = Path(r'D:\FPS3D\资产\模型\Meshy_AI_Rustic_Mountaineering_0919083808_texture.glb')
OUT = HERE / 'Export'
TEXTURES = HERE / 'Textures'
ORIGINAL = HERE / 'Original' / SOURCE.name
for directory in (OUT, TEXTURES, ORIGINAL.parent):
    directory.mkdir(parents=True, exist_ok=True)
if not ORIGINAL.exists():
    shutil.copy2(SOURCE, ORIGINAL)

# Extract the original encoded images without a lossy re-encode. glTF's packed
# material uses G=roughness and B=metallic; those channels stay together in UE.
blob = ORIGINAL.read_bytes()
json_length = struct.unpack_from('<I', blob, 12)[0]
gltf = json.loads(blob[20:20 + json_length])
binary_start = 28 + json_length
for image, name in zip(gltf['images'], ('BaseColor', 'MetallicRoughness', 'Normal')):
    view = gltf['bufferViews'][image['bufferView']]
    start = binary_start + view.get('byteOffset', 0)
    (TEXTURES / (name + '.jpg')).write_bytes(blob[start:start + view['byteLength']])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.import_scene.gltf(filepath=str(ORIGINAL))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
mesh = bpy.context.object
mesh.data.transform(mesh.matrix_world)
mesh.matrix_world = Matrix.Identity(4)
points = [v.co for v in mesh.data.vertices]
low = Vector([min(p[i] for p in points) for i in range(3)])
high = Vector([max(p[i] for p in points) for i in range(3)])
height = .84
scale = height / (high.z - low.z)
mesh.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation(-(low + high) * .5))
mesh.name = 'SM_RusticPickaxe'
mesh.data.name = 'RusticPickaxe_Source'
mesh.data.materials[0].name = 'M_RusticPickaxe'
source_triangles = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
for image in bpy.data.images:
    if image.has_data and not image.packed_file:
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'RusticPickaxe_Fitted_Master.blend'))

report = {'source': str(SOURCE), 'source_sha256': hashlib.sha256(blob).hexdigest(),
          'provenance': 'User supplied Meshy model. Redistribution permission not recorded.',
          'height_m': height, 'scale': scale, 'source_triangles': source_triangles,
          'source_dimensions_m': list(high - low), 'exports': {}, 'runtime_tested': False}
original_data = mesh.data
for tag, count in (('Viewmodel', 96000), ('World', 32000), ('LOD1', 8000), ('LOD2', 2000)):
    mesh.data = original_data.copy()
    modifier = mesh.modifiers.new('Preserve silhouette ' + tag, 'DECIMATE')
    modifier.ratio = min(1., count / source_triangles)
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    for polygon in mesh.data.polygons:
        polygon.use_smooth = True
    path = OUT / ('RusticPickaxe_' + tag + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
        object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
        mesh_smooth_type='FACE', use_tspace=True, bake_anim=False,
        add_leaf_bones=False, path_mode='STRIP')
    report['exports'][tag] = {'file': str(path),
        'triangles': sum(len(p.vertices) - 2 for p in mesh.data.polygons)}
    print('PICKAXE_GEOMETRY_EXPORTED', tag, flush=True)
(HERE / 'model.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
