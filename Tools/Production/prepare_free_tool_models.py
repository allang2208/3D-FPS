"""Fit downloaded Fab tool meshes to the existing centered, Z-up production mount.

Blender --background --python <script> -- <source.fbx/glb> <Axe/Pickaxe> <height_m>
No preview rendering or gameplay tests. Licensed source files stay local.
"""
import bpy
import hashlib
import json
import shutil
import sys
from pathlib import Path
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
source, name, height = Path(args[0]), args[1], float(args[2])
root = Path(__file__).resolve().parents[2]
out = root / 'SourceAssets/FreeProductionTools20260913'
original = out / 'Original' / name / source.name
original.parent.mkdir(parents=True, exist_ok=True)
if not original.exists():
    shutil.copy2(source, original)
dest = out / 'UE'
dest.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
if source.suffix.lower() == '.fbx':
    bpy.ops.import_scene.fbx(filepath=str(source))
else:
    bpy.ops.import_scene.gltf(filepath=str(source))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
if name == 'Axe':
    # The supplied FBX has three disconnected parts: head, wooden handle, metal wedge.
    # Its texture ZIP omits Metalness; preserve a one-material mesh with a vertex mask.
    for obj in meshes:
        adjacency = {v.index: set() for v in obj.data.vertices}
        for edge in obj.data.edges:
            a, b = edge.vertices
            adjacency[a].add(b)
            adjacency[b].add(a)
        remaining = set(adjacency)
        steel = {}
        world_z = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
        full_height = max(world_z) - min(world_z)
        while remaining:
            group = {remaining.pop()}
            todo = list(group)
            while todo:
                for v in adjacency[todo.pop()]:
                    if v in remaining:
                        remaining.remove(v)
                        group.add(v)
                        todo.append(v)
            is_steel = max(world_z[v] for v in group) - min(world_z[v] for v in group) < full_height * .5
            steel.update({v: float(is_steel) for v in group})
        colors = obj.data.color_attributes.new(name='ToolSteelMask', type='BYTE_COLOR', domain='CORNER')
        for loop in obj.data.loops:
            colors.data[loop.index].color = (steel[loop.vertex_index], 0, 0, 1)
        obj.data.color_attributes.active_color = colors
points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
scale = height / (upper.z - lower.z)
# A centered mesh preserves the existing first-person mount and automatic drop centering.
center = (lower + upper) * .5
transform = Matrix.Scale(scale, 4) @ Matrix.Translation(-center)
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:
    obj.matrix_world = transform @ obj.matrix_world
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
if len(meshes) > 1:
    bpy.ops.object.join()
mesh = bpy.context.object
mesh.name = 'SM_Free_' + name
bpy.ops.wm.save_as_mainfile(filepath=str(out / (name + '-fitted.blend')))
bpy.ops.export_scene.fbx(filepath=str(dest / (name + '.fbx')), use_selection=True,
    object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
    axis_forward='-Y', axis_up='Z', mesh_smooth_type='FACE', bake_anim=False,
    use_mesh_modifiers=True, add_leaf_bones=False)
report = {'source': str(source), 'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
          'source_min_m': list(lower), 'source_max_m': list(upper),
          'height_m': height, 'source_scale': scale, 'pivot': 'centered Z up',
          'vertices': len(mesh.data.vertices),
          'triangles': sum(len(p.vertices)-2 for p in mesh.data.polygons),
          'fbx': str(dest / (name + '.fbx')), 'runtime_tested': False}
(out / (name + '-fitting.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
