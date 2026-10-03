"""Restore owned Fab packages at their recorded paths and extract fitting inputs.

Run through mcp_call_codex.ps1 -PythonScript. No scene or play operations.
"""
import json
import zipfile
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/LowerBodyEquipment20261003'
ROOT.mkdir(parents=True, exist_ok=True)
packages = {
    'jeans': ('MetaHuman_Jeans-07dc895c', 'Jeans'),
    'cargo': ('MetaHuman_Cargo_Pants-586d2fd4', 'Cargopants'),
    'sneakers': ('MetaHuman_Casual_Sneakers-7e58d5c5', 'CasualSneakers'),
}
sources = {}
provenance = {}
for key, (folder, part) in packages.items():
    archive = next((PROJECT.parent / 'VaultCache/FabLibrary' / folder).glob('metahuman/UE_5.7/*.mhpkg'))
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('Manifest.json'))
        package_root = manifest['dependentPackages'][0].rsplit('/', 1)[0]
        if not package_root.startswith('/Game/Outfits/'):
            raise RuntimeError('Unexpected package root: ' + package_root)
        dest_root = PROJECT / 'Content' / package_root.removeprefix('/Game/')
        copied = []
        for name in z.namelist():
            if not name.endswith(('.uasset', '.ubulk', '.uexp')):
                continue
            dest = (dest_root / name).resolve()
            if not dest.is_relative_to(dest_root.resolve()):
                raise RuntimeError('Invalid archive path: ' + name)
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as f:
                    f.write(z.read(name))
                copied.append(str(dest.relative_to(PROJECT)))
        provenance[key] = {'archive': str(archive), 'manifest': manifest,
                           'copied': copied, 'redistribution': 'Local project only.'}
    u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([package_root], True)
    sources[key] = package_root + '/' + part + '/meshes/m_med_nrw_CombinedSkelMesh'

config = json.loads((PROJECT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
sources['base'] = config['body_mesh']
sources['body'] = '/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body'
(ROOT / 'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
G, B, Q = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_MeshQueries
def xyz(v): return [v.x, v.y, v.z]
receipt = {}
for key, path in sources.items():
    asset = u.load_asset(path)
    if not asset or not isinstance(asset, u.SkeletalMesh):
        raise RuntimeError('Missing skeletal authoring input: ' + path)
    dm, outcome = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Unable to read mesh: ' + path)
    _, bones = B.get_all_bones_info(dm)
    _, positions, _ = Q.get_all_vertex_positions(dm, False)
    positions = u.GeometryScript_List.convert_vector_list_to_array(positions)
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    weights = []
    for vi in range(len(positions)):
        _, ws, valid = B.get_vertex_bone_weights(dm, vi)
        if not valid: raise RuntimeError('Missing source weights: ' + key)
        weights.append([[w.bone_index, w.weight] for w in ws if w.weight > 0])
    data = {'source': asset.get_path_name(), 'skeleton': asset.skeleton.get_path_name() if asset.skeleton else None,
        'positions': [xyz(v) for v in positions], 'triangles': [xyz(v) for v in triangles],
        'weights': weights,
        'triangle_materials': [u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] for i in range(len(triangles))],
        'materials': [{'slot': str(m.material_slot_name), 'asset': m.material_interface.get_path_name() if m.material_interface else ''} for m in asset.materials],
        'bones': [{'name': str(b.name), 'index': b.index, 'parent': b.parent_index,
            'position': xyz(b.world_transform.translation),
            'axes': [xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                for v in (u.Vector(1,0,0), u.Vector(0,1,0), u.Vector(0,0,1))]} for b in bones]}
    (ROOT / (key + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    receipt[key] = {'source': path, 'vertices': len(positions), 'triangles': len(triangles), 'materials': data['materials'], 'skeleton': data['skeleton']}
    print('LOWER_BODY_SOURCE ' + json.dumps({key: receipt[key]}), flush=True)
(ROOT / 'inputs.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
