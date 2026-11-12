"""Capture current saved garment/head/body geometry through the shared UE bridge."""
import gc
import hashlib
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/ST6FemaleCollar20261108'
manifest = json.loads((WORK / 'manifest.json').read_text())
receipt_file = WORK / 'Inputs/captured.json'
receipt = json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
G, B, Q, L = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_MeshQueries, u.GeometryScript_List


def xyz(v):
    return [v.x, v.y, v.z]


for row in manifest['natives'] + manifest['meshes']:
    source = row['source']
    package = source.split('.')[0]
    digest = hashlib.sha256((PROJECT / 'Content' / (package[6:] + '.uasset')).read_bytes()).hexdigest()
    if package in dirty:
        raise RuntimeError('Keep unsaved source edits before capture: ' + source)
    if receipt.get(source, {}).get('sha256') == digest:
        continue
    asset = u.load_asset(source)
    dm, outcome = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot capture ' + source)
    _, bones = B.get_all_bones_info(dm)
    _, positions, _ = Q.get_all_vertex_positions(dm, False)
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    positions = L.convert_vector_list_to_array(positions)
    triangles = L.convert_triangle_list_to_array(triangles)
    weights = []
    for vertex in range(len(positions)):
        _, influences, valid = B.get_vertex_bone_weights(dm, vertex)
        if not valid:
            raise RuntimeError('Missing source binding: ' + source)
        weights.append([[v.bone_index, v.weight] for v in influences if v.weight > 0])
    data = dict(source=source, source_sha256=digest, skeleton=asset.skeleton.get_path_name(),
        positions=[xyz(v) for v in positions], triangles=[xyz(v) for v in triangles], weights=weights,
        triangle_materials=[u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] for i in range(len(triangles))],
        materials=[dict(slot=str(m.material_slot_name), asset=m.material_interface.get_path_name() if m.material_interface else '') for m in asset.materials],
        bones=[dict(name=str(b.name), index=b.index, parent=b.parent_index, position=xyz(b.world_transform.translation),
            axes=[xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                  for v in (u.Vector(1, 0, 0), u.Vector(0, 1, 0), u.Vector(0, 0, 1))]) for b in bones])
    (WORK / 'Inputs' / row['file']).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    receipt[source] = dict(file=row['file'], sha256=digest)
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ST6_FEMALE_CAPTURED', asset.get_name(), flush=True)
    del data, positions, triangles, weights, bones, dm, asset
    gc.collect()
    u.SystemLibrary.collect_garbage()
print('ST6_FEMALE_CAPTURE_COMPLETE', len(receipt), flush=True)
