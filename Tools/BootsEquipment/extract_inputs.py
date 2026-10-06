"""Read the baked Boots mesh and active Jason coverage base for authoring."""
import json
import shutil
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/BootsEquipment20261004'
prefix = 'Characters/ModularOutfit20260924/BootsEquipment20261004'
donor = prefix + '/Donors/SK_Boots_Donor.uasset'
destination = P / 'Content' / donor
destination.parent.mkdir(parents=True, exist_ok=True)
if not destination.exists():
    shutil.copyfile(P / 'Tools/LowerBodyEquipment/AuthoringHost/Content' / donor, destination)
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/'+prefix, '/Game/Outfits/Boots'], True)
config = json.loads((P / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
body_config = json.loads((P / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
profile_key = body_config['body_mesh']
sources = {'boots': '/Game/' + donor.removesuffix('.uasset'), 'base': config['profiles'][profile_key]['base']}
for key, definition in [('jeans', 'ue_jeans'), ('cargo', 'ue_cargo_pants')]:
    sources[key] = config['items'][definition]['rig_meshes']['Jason']
G, B, Q = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_MeshQueries
def xyz(v): return [v.x, v.y, v.z]
for key, path in sources.items():
    asset = u.load_asset(path)
    if not isinstance(asset, u.SkeletalMesh): raise RuntimeError('Missing skeletal input: '+path)
    dm, outcome = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read '+path)
    _, bones = B.get_all_bones_info(dm)
    _, vectors, _ = Q.get_all_vertex_positions(dm, False)
    positions = u.GeometryScript_List.convert_vector_list_to_array(vectors)
    _, indices, _ = Q.get_all_triangle_indices(dm, False)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(indices)
    weights = []
    for vi in range(len(positions)):
        _, ws, valid = B.get_vertex_bone_weights(dm, vi)
        if not valid: raise RuntimeError('Missing source weights')
        weights.append([[w.bone_index, w.weight] for w in ws if w.weight > 0])
    data = {'source': asset.get_path_name(), 'skeleton': asset.skeleton.get_path_name() if asset.skeleton else None,
            'positions': [xyz(v) for v in positions], 'triangles': [xyz(v) for v in triangles], 'weights': weights,
            'triangle_materials': [u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] for i in range(len(triangles))],
            'materials': [{'slot': str(m.material_slot_name), 'asset': m.material_interface.get_path_name() if m.material_interface else ''} for m in asset.materials],
            'bones': [{'name': str(b.name), 'index': b.index, 'parent': b.parent_index, 'position': xyz(b.world_transform.translation),
                       'axes': [xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]} for b in bones]}
    (R / (key + '.json')).write_text(json.dumps(data, separators=(',',':')), encoding='utf-8')
    print('BOOTS_INPUT', key, len(positions), len(triangles), flush=True)
(R / 'profile.json').write_text(json.dumps({'profile_key':profile_key, 'previous_base':sources['base']}, indent=2))
