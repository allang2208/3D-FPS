"""Read M16's loaded asset contract and actual native arm surfaces."""
import json
import hashlib
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
O = Path(__file__).parent
OUT = O / 'Input'
OUT.mkdir(parents=True, exist_ok=True)
C = json.loads((P / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
SOURCE = '/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny.SK_M16_Manny'
profile = C['profiles'][SOURCE]
Q, B, G = u.GeometryScript_MeshQueries, u.GeometryScript_BoneWeights, u.GeometryScript_AssetUtils
R = {'source': SOURCE, 'profile': profile, 'assets': {}}

def xyz(v):
    return [v.x, v.y, v.z]

for key, path in [('CurrentM16', SOURCE), ('AcceptedM16V7', profile['base']),
                  ('EquipmentM16Skin', profile['native_bare_skin'])]:
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing asset ' + path)
    dm, status = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read current mesh ' + path)
    _, bones = B.get_all_bones_info(dm)
    names = {b.index: str(b.name) for b in bones}
    _, positions, _ = Q.get_all_vertex_positions(dm, False)
    ps = u.GeometryScript_List.convert_vector_list_to_array(positions)
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    ts = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    slots = [{'slot': str(s.material_slot_name), 'material': s.material_interface.get_path_name() if s.material_interface else None} for s in asset.materials]
    arm_ids = profile['hide_source_materials'] if key == 'CurrentM16' else list(range(len(slots)))
    faces, materials = [], []
    for i, t in enumerate(ts):
        mat, valid = u.GeometryScript_Materials.get_triangle_material_id(dm, i)
        if valid and mat in arm_ids:
            faces.append(xyz(t))
            materials.append(mat)
    ids = sorted({v for t in faces for v in t})
    remap = {v: i for i, v in enumerate(ids)}
    weights = []
    for vi in ids:
        _, ws, valid = B.get_vertex_bone_weights(dm, vi)
        if not valid:
            raise RuntimeError('Missing binding ' + key)
        weights.append({names[w.bone_index]: w.weight for w in ws if w.weight > 0})
    source_file = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    data = {'path': path, 'skeleton': asset.skeleton.get_path_name(), 'slots': slots,
        'arm_ids': arm_ids, 'source_sha256': hashlib.sha256(source_file.read_bytes()).hexdigest(),
        'positions': [xyz(ps[i]) for i in ids], 'weights': weights,
        'triangles': [[remap[v] for v in t] for t in faces], 'triangle_materials': materials,
        'bones': {str(b.name): {'index': b.index, 'parent': b.parent_index,
            'position': xyz(b.world_transform.translation),
            'axes': [xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                     for v in (u.Vector(1, 0, 0), u.Vector(0, 1, 0), u.Vector(0, 0, 1))]} for b in bones}}
    (OUT / (key + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    R['assets'][key] = {k: v for k, v in data.items() if k not in ['positions', 'weights', 'triangles', 'triangle_materials', 'bones']}
    R['assets'][key].update(vertices=len(ids), arm_triangles=len(faces),
        bare_metadata=u.EditorAssetLibrary.get_metadata_tag(asset, 'BareArmsDefault'))
    u.log('CLOVEN_M16_HAND_INPUT ' + key + ' vertices=' + str(len(ids)))
(O / 'hand_sources.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
u.log('CLOVEN_M16_HAND_SOURCES_READ')
