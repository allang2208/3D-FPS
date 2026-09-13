"""Fit the downloaded Basic Pickaxe while keeping its three authored LODs separate.

Blender --background --python <script> -- <source directory> [height_m]
Licensed originals and exported binaries remain local. No preview or gameplay tests.
"""
import bpy
import hashlib
import json
import shutil
import sys
from pathlib import Path
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
source = Path(args[0])
height = float(args[1]) if len(args) > 1 else 0.70
root = Path(__file__).resolve().parents[2]
out = root / 'SourceAssets/FreeProductionTools20260913'
original = out / 'Original/Pickaxe'
dest = out / 'UE'
original.mkdir(parents=True, exist_ok=True)
dest.mkdir(parents=True, exist_ok=True)
files = ['SM_BasicPickaxe.fbx'] + [f'T_BasicPickaxe_{channel}.tga' for channel in
    ['BaseColor', 'Normal', 'Metallic', 'Roughness', 'Occlusion']]
sources = {}
for name in files:
    shutil.copy2(source / name, original / name)
    sources[name] = hashlib.sha256((original / name).read_bytes()).hexdigest()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(original / 'SM_BasicPickaxe.fbx'))
lods = [bpy.data.objects[f'BasicPickaxe_LOD{i}'] for i in range(3)]
points = [lods[0].matrix_world @ vertex.co for vertex in lods[0].data.vertices]
lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
scale = height / (upper.z - lower.z)
center = (lower + upper) * .5
# One common transform keeps all three authored LODs aligned when switching.
transform = Matrix.Scale(scale, 4) @ Matrix.Translation(-center)
report = {'source': str(source), 'sources_sha256': sources, 'height_m': height,
          'source_scale': scale, 'pivot': 'centered Z up',
          'source_min_m': list(lower), 'source_max_m': list(upper),
          'size_m': list((upper - lower) * scale), 'lods': [], 'runtime_tested': False}
for index, obj in enumerate(lods):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.matrix_world = transform @ obj.matrix_world
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.name = f'SM_Free_Pickaxe_LOD{index}'
    file = dest / f'Pickaxe_LOD{index}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(file), use_selection=True,
        object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
        axis_forward='-Y', axis_up='Z', mesh_smooth_type='FACE', bake_anim=False,
        use_mesh_modifiers=True, add_leaf_bones=False)
    report['lods'].append({'index': index, 'vertices': len(obj.data.vertices),
        'triangles': sum(len(p.vertices) - 2 for p in obj.data.polygons), 'fbx': str(file)})

# Show only LOD0 when the editable source is opened; the lower LODs are still retained.
for index, obj in enumerate(lods):
    obj.hide_set(index > 0)
    obj.hide_render = index > 0
bpy.ops.object.select_all(action='DESELECT')
lods[0].select_set(True)
bpy.context.view_layer.objects.active = lods[0]
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Pickaxe-fitted.blend'))
(out / 'Pickaxe-fitting.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
