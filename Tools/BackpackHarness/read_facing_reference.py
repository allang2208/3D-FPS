"""Read UE's own cube as the front-face convention reference."""
import json
from pathlib import Path
import unreal as u

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BackpackHarnessRebuild20261020/FacingRepair20261022')
R.mkdir(parents=True, exist_ok=True)
mesh = u.load_asset('/Engine/BasicShapes/Cube.Cube')
dm, status = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh, u.DynamicMesh(),
    u.GeometryScriptCopyMeshFromAssetOptions(),
    u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA, lod_index=0))
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot read engine cube reference')
Q, L = u.GeometryScript_MeshQueries, u.GeometryScript_List
_, vertices, _ = Q.get_all_vertex_positions(dm, False)
_, triangles, _ = Q.get_all_triangle_indices(dm, False)
vec = lambda v: [v.x, v.y, v.z]
vertices = [vec(v) for v in L.convert_vector_list_to_array(vertices)]
triangles = [vec(t) for t in L.convert_triangle_list_to_array(triangles)]
normals = []
for ti in range(len(triangles)):
    _, a, b, c, valid = Q.get_triangle_normals(dm, ti)
    if not valid:
        raise RuntimeError('Cube normals unavailable')
    normals.append([vec(n) for n in (a, b, c)])
(R/'ue_cube_reference.json').write_text(json.dumps({'asset': mesh.get_path_name(),
    'lod_type': 'RenderData', 'positions': vertices, 'triangles': triangles, 'normals': normals}, indent=2))
print('UE_FACING_REFERENCE_SAVED', flush=True)
