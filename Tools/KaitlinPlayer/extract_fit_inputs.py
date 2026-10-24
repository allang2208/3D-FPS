"""Read a bounded batch of saved equipment meshes from the active FPSGAME editor.

Run through the existing MCP Python batch gate. Only the task's JSON authoring
inputs are written; no existing game asset or live component is edited.
"""
import gc
import hashlib
import json
import time
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/KaitlinPlayer20261023/FitInputs'
inventory = json.loads((WORK / 'inventory.json').read_text(encoding='utf-8'))
receipt_path = WORK / 'captured.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
G, B, Q, L = (u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights,
               u.GeometryScript_MeshQueries, u.GeometryScript_List)
started = time.monotonic()
written = 0
capture_all = '-KaitlinCaptureAll' in u.SystemLibrary.get_command_line()
dirty_packages = {package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def xyz(value):
    return [value.x, value.y, value.z]


pending = []
only_sources = set(globals().get('ONLY_SOURCES', []))
for row in inventory['meshes']:
    path = row['source']
    if only_sources and path not in only_sources:
        continue
    source_file = PROJECT / 'Content' / (path.split('.', 1)[0][len('/Game/'):] + '.uasset')
    digest = hashlib.sha256(source_file.read_bytes()).hexdigest()
    output = WORK / row['file']
    if receipt.get(path, {}).get('source_sha256') == digest and output.exists():
        continue
    pending.append((row, digest))

for row, digest in pending:
    path = row['source']
    output = WORK / row['file']
    if path.split('.', 1)[0] in dirty_packages:
        raise RuntimeError('Source has unsaved editor edits; retain it before taking a saved-mesh snapshot: ' + path)
    asset = u.load_asset(path)
    if not isinstance(asset, u.SkeletalMesh):
        raise RuntimeError('Expected a skeletal authoring source: ' + path)
    dm, outcome = G.copy_mesh_from_skeletal_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read saved source: ' + path)
    _, bones = B.get_all_bones_info(dm)
    _, positions, _ = Q.get_all_vertex_positions(dm, False)
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    positions = L.convert_vector_list_to_array(positions)
    triangles = L.convert_triangle_list_to_array(triangles)
    weights = []
    for vertex in range(len(positions)):
        _, vertex_weights, valid = B.get_vertex_bone_weights(dm, vertex)
        if not valid:
            raise RuntimeError('Missing skin weights: ' + path)
        weights.append([[w.bone_index, w.weight] for w in vertex_weights if w.weight > 0])
    data = {
        'source': path, 'source_sha256': digest, 'skeleton': asset.skeleton.get_path_name(),
        'positions': [xyz(v) for v in positions], 'triangles': [xyz(v) for v in triangles],
        'weights': weights,
        'materials': [{'slot': str(m.material_slot_name),
                       'asset': m.material_interface.get_path_name() if m.material_interface else ''}
                      for m in asset.materials],
        'triangle_materials': [u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0]
                               for i in range(len(triangles))],
        'bones': [{'name': str(b.name), 'index': b.index, 'parent': b.parent_index,
                   'position': xyz(b.world_transform.translation),
                   'axes': [xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                            for v in (u.Vector(1, 0, 0), u.Vector(0, 1, 0), u.Vector(0, 0, 1))]}
                  for b in bones],
    }
    output.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    receipt[path] = {'file': row['file'], 'source_sha256': digest,
                     'vertices': len(positions), 'triangles': len(triangles)}
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('KAITLIN_FIT_SOURCE_SAVED', path, flush=True)
    written += 1
    del data, positions, triangles, weights, bones, dm, asset
    gc.collect()
    u.SystemLibrary.collect_garbage()
    if capture_all and written >= 24 or not capture_all and (written >= 6 or time.monotonic() - started >= 65):
        break
(WORK / 'capture_status.json').write_text(json.dumps({
    'remaining': len(pending) - written, 'current_scope': len(inventory['meshes']),
    'written': written, 'complete': written == len(pending)}), encoding='utf-8')
print('KAITLIN_FIT_CAPTURE_BATCH', written, 'saved;', len(pending) - written, 'remaining')
