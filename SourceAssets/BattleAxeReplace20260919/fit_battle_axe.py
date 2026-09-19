"""Fit the Meshy battle axe to the production-mount conventions and decimate it.

Blender --background --python <this> -- <source.fbx> <out_dir> <height_m> <target_tris> <tag>

Matches prepare_free_tool_models.py except for one deliberate difference: the source blade
faces -X while the retired axe blade faces +X, so the mesh turns 180 deg around Z before the
shared centering. Geometry is decimated to the target triangle count for game use.
No gameplay tests, no acceptance claims.
"""
import bpy
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
source = Path(args[0])
out_dir = Path(args[1])
height = float(args[2])
target_tris = int(args[3])
tag = args[4]
out_dir.mkdir(parents=True, exist_ok=True)

original = out_dir / 'Original' / source.name
original.parent.mkdir(parents=True, exist_ok=True)
if not original.exists():
    shutil.copy2(source, original)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(source))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
source_report = {
    'objects': [o.name for o in meshes],
    'vertices': sum(len(o.data.vertices) for o in meshes),
    'triangles': sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons),
    'custom_normals': [bool(o.data.has_custom_normals) for o in meshes],
    'uv_layers': [list(o.data.uv_layers.keys()) for o in meshes],
}
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
mesh = bpy.context.object
# Bake the importer transform so the turn and fit act in world coordinates.
mesh.data.transform(mesh.matrix_world)
mesh.matrix_world = Matrix.Identity(4)

# The retired axe blade faces +X; this source faces -X. Align before anything else.
mesh.data.transform(Matrix.Rotation(math.radians(180), 4, 'Z'))

points = [v.co for v in mesh.data.vertices]
lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
scale = height / (upper.z - lower.z)
center = (lower + upper) * .5
# Centered Z-up pivot: the existing first-person mount and drop centering both rely on it.
mesh.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation(-center))

before = len(mesh.data.polygons)
ratio = min(1., target_tris / max(1, before))
modifier = mesh.modifiers.new('GameGeometry', 'DECIMATE')
modifier.decimate_type = 'COLLAPSE'
modifier.ratio = ratio
modifier.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=modifier.name)
for polygon in mesh.data.polygons:
    polygon.use_smooth = True
mesh.name = 'SM_BattleAxe'
mesh.data.name = 'SM_BattleAxe'

dest = out_dir / (tag + '.fbx')
bpy.ops.export_scene.fbx(filepath=str(dest), use_selection=True,
    object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
    axis_forward='-Y', axis_up='Z', mesh_smooth_type='FACE', bake_anim=False,
    use_mesh_modifiers=True, add_leaf_bones=False)

points = [v.co for v in mesh.data.vertices]
lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
grip_z = -.26
section = [p for p in points if abs(p.z - grip_z) < .06]
report = {
    'source': str(source), 'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
    'source_report': source_report, 'height_m': height, 'fit_scale': scale,
    'turn_degrees': 180,
    'triangles_before': before, 'triangles_after': len(mesh.data.polygons), 'decimate_ratio': ratio,
    'min': [round(v, 4) for v in lower], 'max': [round(v, 4) for v in upper],
    'grip_z': grip_z,
    'grip_section': {
        'count': len(section),
        'x': [round(min(p.x for p in section), 4), round(max(p.x for p in section), 4)],
        'y': [round(min(p.y for p in section), 4), round(max(p.y for p in section), 4)],
    },
    'blade_tip_x': round(max(p.x for p in points), 4),
    'poll_x': round(min(p.x for p in points), 4),
    'fbx': str(dest), 'runtime_tested': False,
}
(out_dir / (tag + '-fit.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))