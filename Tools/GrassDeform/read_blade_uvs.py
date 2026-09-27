"""Read per-triangle PivotPainter UV coherence from all existing render LODs."""
import json
from pathlib import Path
import unreal as u

out = Path(u.Paths.project_saved_dir()) / 'GrassShape20260927'
out.mkdir(parents=True, exist_ok=True)
report = {}
Q = u.GeometryScript_MeshQueries
for name in ['SM_Meadow_grass_03_08_mesh', 'SM_Meadow_grass_05_03_mesh']:
    mesh = u.load_asset('/Game/WorldGeneration/TemperateHills/Grass/' + name)
    rows = []
    for lod_index in range(mesh.get_num_lods()):
        lod = u.GeometryScriptMeshReadLOD()
        lod.set_editor_property('lod_type', u.GeometryScriptLODType.RENDER_DATA)
        lod.set_editor_property('lod_index', lod_index)
        dyn = u.DynamicMesh()
        _, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dyn, u.GeometryScriptCopyMeshFromAssetOptions(), lod)
        max_spread = 0.0
        roots = set()
        _, triangles, _ = Q.get_all_triangle_indices(dyn, True)
        count = len(u.GeometryScript_List.convert_triangle_list_to_array(triangles))
        for triangle in range(count):
            a, b, c, valid = Q.get_triangle_u_vs(dyn, 1, triangle)
            if not valid:
                raise RuntimeError('Missing PivotPainter UVs: ' + name)
            max_spread = max(max_spread, abs(a.x-b.x), abs(a.y-b.y), abs(a.x-c.x), abs(a.y-c.y))
            roots.add((round(a.x,6), round(a.y,6)))
        rows.append({'lod': lod_index, 'triangles': count, 'pivot_uv_groups': len(roots), 'max_triangle_uv_spread': max_spread})
    report[name] = rows
(out / 'blade-uvs.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BLADE_UVS ' + json.dumps(report))
