"""Export the original segmented flux tube in Blender background; no render."""
import bpy
import json
import math
from pathlib import Path

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/ThunderLanceFlux20261001')
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
SIDES, SEGMENTS = 32, 48
vertices, faces = [], []
for j in range(SEGMENTS + 1):
    z = j / SEGMENTS - .5
    for i in range(SIDES + 1):
        a = i * math.tau / SIDES
        vertices.append((.5 * math.cos(a), .5 * math.sin(a), z))
for j in range(SEGMENTS):
    for i in range(SIDES):
        a = j * (SIDES + 1) + i
        b = a + SIDES + 1
        faces.append((a, a + 1, b + 1, b))
side_face_count = len(faces)
for end in (0, SEGMENTS):
    center = len(vertices)
    vertices.append((0., 0., end / SEGMENTS - .5))
    for i in range(SIDES):
        a = end * (SIDES + 1) + i
        faces.append((center, a + 1, a) if end == 0 else (center, a, a + 1))
mesh = bpy.data.meshes.new('ThunderFluxTube')
mesh.from_pydata(vertices, [], faces)
mesh.update()
obj = bpy.data.objects.new('SM_ThunderFluxTube', mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
uv = mesh.uv_layers.new(name='FlowUV')
for polygon in mesh.polygons:
    polygon.use_smooth = polygon.index < side_face_count
    for loop_index in polygon.loop_indices:
        index = mesh.loops[loop_index].vertex_index
        if polygon.index < side_face_count:
            uv.data[loop_index].uv = (index // (SIDES + 1) / SEGMENTS, index % (SIDES + 1) / SIDES)
        else:
            p = vertices[index]
            uv.data[loop_index].uv = (p[0] + .5, p[1] + .5)
bpy.ops.export_scene.fbx(filepath=str(OUT / 'SM_ThunderFluxTube.fbx'), use_selection=True,
                         apply_unit_scale=True, axis_forward='-Y', axis_up='Z',
                         add_leaf_bones=False, object_types={'MESH'})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'thunder_flux_tube.blend'))
(OUT / 'mesh-production.json').write_text(json.dumps({
    'source': 'original procedural geometry', 'unit': 'metres', 'axis': '+Z',
    'diameter_m': 1, 'length_m': 1, 'axial_segments': SEGMENTS, 'sides': SIDES,
    'vertices': len(vertices), 'triangles': side_face_count * 2 + SIDES * 2,
    'collision': False, 'rendered': False}, indent=2), encoding='utf-8')
print('THUNDER_FLUX_MESH_EXPORTED')
