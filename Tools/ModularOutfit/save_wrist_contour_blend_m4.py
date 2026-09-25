"""Save the V4 editable source with native rig, weights and the new wrist skin."""
import json
import runpy
from pathlib import Path
import bpy

PROJECT = Path('D:/FPS3D/FPSGAME')
BASE = PROJECT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'
ROOT = BASE / 'WristContourV4'
source = json.loads((ROOT / 'M4_original.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(BASE / 'RefinedSkinV3/M4_OriginalShape_BareHands_Editable.blend'))
obj = bpy.data.objects['M4_OriginalShape_BareHands']
mesh = bpy.data.meshes.new('M4_WristContourV4_NativeBinding')
# One handedness reflection, no additional face reversal (the V3 winding fix).
mesh.from_pydata([(p[0]*.01, -p[1]*.01, p[2]*.01) for p in source['positions']], [], source['triangles'])
mesh.update()
for material in obj.data.materials[:3]:
    mesh.materials.append(material)
obj.data = mesh
obj.vertex_groups.clear()
for name in sorted({n for w in source['weights'] for n in w}):
    obj.vertex_groups.new(name=name)
for i, weights in enumerate(source['weights']):
    for name, value in weights.items():
        obj.vertex_groups[name].add([i], value, 'REPLACE')
uv = mesh.uv_layers.new(name='NativeGrip_SkinUV')
normals = []
for polygon, coords, mat, ns in zip(mesh.polygons, source['uv'], source['triangle_materials'], source['normals']):
    polygon.material_index = mat
    polygon.use_smooth = True
    for loop, (u, v), n in zip(polygon.loop_indices, coords, ns):
        uv.data[loop].uv = (u, 1-v)
        normals.append((n[0], -n[1], n[2]))
mesh.normals_split_custom_set(normals)
obj['AuthoringContract'] = 'V4 local wrist contour; corrected V3 connectivity, grip, native weights and reference rig retained'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'M4_OriginalShape_BareHands_Editable.blend'))
runpy.run_path(str(PROJECT / 'Tools/ModularOutfit/finish_refined_skin_blend_m4.py'),
              init_globals={'AUTHOR_ROOT': str(ROOT)})
