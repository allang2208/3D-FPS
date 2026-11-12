"""Save a resumable batch into new female-only ST6 packages, using the UE bridge."""
import gc
import hashlib
import json
import runpy
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/ST6FemaleCollar20261108'
manifest = json.loads((WORK / 'manifest.json').read_text())
if not manifest.get('authored'):
    raise RuntimeError('Author the head-derived collar first')
hook = runpy.run_path(str(PROJECT / 'Tools/ST6FemaleCollar/apply.py'))
E, G = u.EditorAssetLibrary, u.GeometryScript_AssetUtils
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt_path = WORK / 'saved_assets.json'
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(meshes={}, runtime_tested=False)
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
if level and level.is_in_play_in_editor():
    raise RuntimeError('End play before clothing asset production')
patch_hash = hashlib.sha256((WORK / 'collar.json').read_bytes()).hexdigest()
if patch_hash != manifest['collar_sha256']:
    raise RuntimeError('Collar source changed after authoring')
for native in manifest['natives']:
    data = json.loads((WORK / 'Inputs' / native['file']).read_text())
    source_file = PROJECT / 'Content' / (native['source'].split('.')[0][6:] + '.uasset')
    if hashlib.sha256(source_file.read_bytes()).hexdigest() != data['source_sha256']:
        raise RuntimeError('Native head/body changed; regenerate this collar')
completed = 0
for row in manifest['meshes']:
    source = row['source']
    if source in receipt['meshes']:
        if receipt['meshes'][source]['collar_sha256'] != patch_hash:
            raise RuntimeError('Saved revision has different collar geometry')
        continue
    if source.split('.')[0] in dirty or row['asset'] in dirty:
        raise RuntimeError('Retain unsaved source/output edits before this batch')
    source_file = PROJECT / 'Content' / (source.split('.')[0][6:] + '.uasset')
    if hashlib.sha256(source_file.read_bytes()).hexdigest() != row['source_sha256']:
        raise RuntimeError('ST6 source changed after capture: ' + source)
    if E.does_asset_exist(row['asset']):
        raise RuntimeError('Output exists without a save receipt: ' + row['asset'])
    original = u.load_asset(source)
    mesh, outcome = G.copy_mesh_from_skeletal_mesh(original, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read original ST6 mesh')
    data = json.loads((WORK / 'Inputs' / row['file']).read_text())
    if not hook['replace_collar'](mesh, data['materials']):
        raise RuntimeError('Missing ST6 neckline material slot')
    asset = E.duplicate_asset(source, row['asset'])
    options = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False, enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, outcome = G.copy_mesh_to_skeletal_mesh(mesh, asset, options, u.GeometryScriptMeshWriteLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot write female ST6 collar')
    hook['configure_lods'](asset)
    if not S.regenerate_lod(asset, 3, True, False):
        raise RuntimeError('Cannot finish collar LOD production')
    E.set_metadata_tag(asset, 'ST6FemaleCollarSource', patch_hash)
    E.set_metadata_tag(asset, 'ST6FemaleCollarOriginal', source)
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save female ST6 collar')
    receipt['meshes'][source] = dict(asset=asset.get_path_name(), collar_sha256=patch_hash,
        original_sha256=row['source_sha256'], lod_count=S.get_lod_count(asset), triangles=mesh.get_triangle_count())
    receipt['completed'] = len(receipt['meshes']) == len(manifest['meshes'])
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ST6_FEMALE_SAVED', asset.get_name(), flush=True)
    del original, asset, mesh, data
    gc.collect()
    u.SystemLibrary.collect_garbage()
    completed += 1
    if completed >= 6:
        break
print('ST6_FEMALE_SAVE_PROGRESS', len(receipt['meshes']), '/', len(manifest['meshes']), flush=True)
