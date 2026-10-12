"""Read render-slot routing and the source polygon-group identities."""
import json, gzip, collections
from pathlib import Path
import unreal as u
O = Path(__file__).parent
mesh = u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
G = u.GeometryScript_AssetUtils
Q = u.GeometryScript_MeshQueries
materials, indices, names, status = G.get_lod_material_list_from_skeletal_mesh(mesh, u.GeometryScriptMeshReadLOD())
dm, status = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot read existing source geometry')
_, positions, _ = Q.get_all_vertex_positions(dm, False)
positions = u.GeometryScript_List.convert_vector_list_to_array(positions)
_, triangles, _ = Q.get_all_triangle_indices(dm, False)
triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
ids = [u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] for i in range(len(triangles))]
data = {'lod_material_indices': list(indices), 'lod_slot_names': [str(n) for n in names],
        'lod_materials': [m.get_path_name() if m else None for m in materials],
        'face_count_by_source_id': dict(collections.Counter(ids)),
        'api': G.copy_mesh_to_skeletal_mesh.__doc__}
(O / 'sections.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
with gzip.open(O / 'source_geometry.json.gz', 'wt', encoding='utf-8') as f:
    json.dump({'positions': [[p.x, p.y, p.z] for p in positions],
               'triangles': [[t.x, t.y, t.z] for t in triangles], 'materials': ids}, f)
print(json.dumps(data, indent=2))
