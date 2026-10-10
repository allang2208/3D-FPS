"""Freeze installed crown interfaces and head envelopes for offline authoring."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/Weapons/ApprenticeStaff20260927'
keys = ['spike_crown', 'current_crown', 'wreath_crown', 'heat_crown']
names = ['SM_Staff_crown_' + k for k in keys]
names += ['SM_Staff_head_crystal_' + k for k in
          ['false', 'frozen_crystal', 'jade_spirit_crystal', 'magma_core', 'storm_core']]
result = {'units': 'cm', 'assets': []}
for name in names:
    asset = u.load_asset(BASE + '/Meshes/' + name)
    if not asset:
        raise RuntimeError('Missing authoring input: ' + name)
    dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot extract ' + name)
    _, vs, _ = u.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
    _, ts, _ = u.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
    vs = u.GeometryScript_List.convert_vector_list_to_array(vs)
    ts = u.GeometryScript_List.convert_triangle_list_to_array(ts)
    mids = []
    for i in range(len(ts)):
        mid, valid = u.GeometryScript_Materials.get_triangle_material_id(dm, i)
        if not valid:
            raise RuntimeError('Noncompact input mesh ' + name)
        mids.append(mid)
    result['assets'].append(dict(name=name, source=asset.get_path_name(),
        vertices=[[v.x, v.y, v.z] for v in vs], triangles=[[t.x,t.y,t.z] for t in ts],
        material_ids=mids, materials=[s.material_interface.get_path_name() if s.material_interface else ''
                                    for s in asset.static_materials]))
(ROOT/'installed-inputs.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
print('CROWN_INPUTS_CAPTURED ' + str(len(result['assets'])))
