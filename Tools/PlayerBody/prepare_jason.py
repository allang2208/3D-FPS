"""Migrate the owned Jason package and extract inputs for body/outfit authoring.

Run in Unreal Python via the project MCP batch mutex, or a background commandlet.
Does not change the map, spawn actors, start PIE, or publish runtime defaults.
"""
from pathlib import Path
import json
import shutil
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/JasonPlayer20261003'
SOURCE = Path('D:/FPS3D/AsianMaleJason/Content/AsianMale_Jason')
DEST = PROJECT / 'Content/AsianMale_Jason'
ROOT.mkdir(parents=True, exist_ok=True)
copied = []
for path in SOURCE.rglob('*'):
    if not path.is_file():
        continue
    target = DEST / path.relative_to(SOURCE)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(str(path.relative_to(SOURCE)))
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/AsianMale_Jason'], True)
G, B, Q = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_MeshQueries
config = json.loads((PROJECT / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
profile = config['profiles']['/Game/Characters/Mannequins/PlayerBodySkin/SKM_Manny_PlayerSkin.SKM_Manny_PlayerSkin']
sources = {'Jason': '/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body',
           'Manny': '/Game/Characters/Mannequins/PlayerBodySkin/SKM_Manny_PlayerSkin',
           'NativeSkin': profile['native_bare_skin']}
for key, item in config['items'].items():
    path = item.get('rig_meshes', {}).get('Body')
    if path:
        sources[key] = path
    path = item.get('skin_meshes', {}).get('Body')
    if path:
        sources[key + '_skin'] = path

def xyz(v):
    return [v.x, v.y, v.z]

manifest = {}
for key, path in sources.items():
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing authoring input: ' + path)
    dm, outcome = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot extract source: ' + path)
    _, bones = B.get_all_bones_info(dm)
    _, positions, _ = Q.get_all_vertex_positions(dm, False)
    positions = u.GeometryScript_List.convert_vector_list_to_array(positions)
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    weights = []
    for vi in range(len(positions)):
        _, ws, valid = B.get_vertex_bone_weights(dm, vi)
        if not valid:
            raise RuntimeError('Missing weights: ' + key)
        weights.append([[w.bone_index, w.weight] for w in ws if w.weight > 0])
    materials = []
    for slot in asset.materials:
        materials.append({'slot': str(slot.material_slot_name),
                          'asset': slot.material_interface.get_path_name() if slot.material_interface else ''})
    data = {'source': path, 'positions': [xyz(v) for v in positions],
            'triangles': [xyz(v) for v in triangles], 'weights': weights,
            'bones': [{'name': str(b.name), 'index': b.index, 'parent': b.parent_index,
                       'position': xyz(b.world_transform.translation),
                       'axes': [xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                                for v in (u.Vector(1,0,0), u.Vector(0,1,0), u.Vector(0,0,1))]}
                      for b in bones], 'materials': materials}
    (ROOT / (key + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    manifest[key] = {'path': path, 'vertices': len(positions), 'triangles': len(triangles), 'bones': len(bones)}
    print('JASON_INPUT_SAVED ' + key, flush=True)
(ROOT / 'inputs.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(ROOT / 'provenance.json').write_text(json.dumps({
    'listing': 'https://www.fab.com/listings/40dd9e51-0a33-4cf9-9f62-da3ab0ff840b',
    'name': 'AsianMale Jason', 'publisher': 'Vedia Generation',
    'source_project': 'D:/FPS3D/AsianMaleJason',
    'acquisition': 'User-provided local Fab download; authorized project integration.',
    'redistribution': 'Original and derived binary assets remain local; no public redistribution authorized.',
    'copied_files': copied}, indent=2), encoding='utf-8')
print('JASON_PREPARE_COMPLETE ' + json.dumps(manifest), flush=True)
