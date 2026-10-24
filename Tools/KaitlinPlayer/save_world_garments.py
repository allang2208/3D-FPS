"""Save a bounded batch of native female skeletal garments in FPSGAME."""
import gc
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
extra_path = WORK / 'FitInputs/extra_equipment_pending.json'
if extra_path.exists():
    import runpy
    extra = json.loads(extra_path.read_text())
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/KaitlinPlayer/extract_fit_inputs.py',
                  init_globals={'ONLY_SOURCES': extra['sources']}, run_name='__main__')
    if not json.loads((WORK / 'FitInputs/capture_status.json').read_text())['complete']:
        raise RuntimeError('Finish the additional equipment source capture before resuming.')
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/KaitlinPlayer/capture_pack_masks.py', run_name='__main__')
    extra_path.unlink()
folder = globals().get('FIT_FOLDER', 'WorldGarments')
stage = globals().get('FIT_STAGE', 'save_world_garments')
if not (WORK / 'ViewSkin/material_inputs.json').exists():
    import runpy
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/KaitlinPlayer/capture_skin_materials.py', run_name='__main__')
manifest = json.loads((WORK / folder / 'manifest.json').read_text(encoding='utf-8'))
target_path = json.loads((WORK / 'full_body_receipt.json').read_text(encoding='utf-8'))['mesh']
target = u.load_asset(target_path)
G, B, L = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_List
E = u.EditorAssetLibrary
receipt_path = WORK / folder / 'saved_assets.json'
saved = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}


def dynamic(asset):
    mesh, outcome = G.copy_mesh_from_skeletal_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read garment geometry: ' + asset.get_path_name())
    return mesh


target_mesh = dynamic(target)
_, target_bones = B.get_all_bones_info(target_mesh)
target_bone_names = [str(bone.name) for bone in target_bones]
completed = 0
for source, row in manifest.items():
    if source in saved:
        continue
    if E.does_asset_exist(row['asset']):
        raise RuntimeError('Existing garment output has no save receipt: ' + row['asset'])
    data = json.loads(Path(row['geometry']).read_text(encoding='utf-8'))
    mesh = dynamic(u.load_asset(source))
    _, source_bones = B.get_all_bones_info(mesh)
    same_bone_indices = [str(bone.name) for bone in source_bones] == target_bone_names
    B.copy_bones_from_mesh(target_mesh, mesh, u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=False))
    positions = L.convert_array_to_vector_list([u.Vector(*point) for point in data['positions']])
    u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(mesh, positions)
    # Jason and Kaitlin share the native 342-bone index order. Retain those
    # authored weights verbatim; only a different hierarchy needs remapping.
    if not same_bone_indices:
        for index, weights in enumerate(data['weights']):
            B.set_vertex_bone_weights(mesh, index, [u.GeometryScriptBoneWeight(bone_index=bone, weight=weight)
                                                   for bone, weight in weights])
    options = u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    options.use_mesh_bone_proportions = True
    options.enable_recompute_normals = True
    options.enable_recompute_tangents = True
    options.materials = {material['slot']: u.load_asset(material['asset']) for material in data['materials']}
    asset, outcome = u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(
        mesh, target.skeleton, row['asset'], options)
    if outcome != u.GeometryScriptOutcomePins.SUCCESS or not asset:
        raise RuntimeError('Female garment creation failed: ' + row['asset'])
    # Carry the project's existing outfit distance-LOD policy; keep authored LOD0.
    if not u.FPSModularOutfitComponent.configure_outfit_lods(asset):
        raise RuntimeError('Could not apply existing outfit LOD policy: ' + row['asset'])
    if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(asset, 3, True, False):
        raise RuntimeError('Garment LOD build did not finish: ' + row['asset'])
    asset.set_editor_property('physics_asset', target.physics_asset)
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Female garment save failed: ' + row['asset'])
    saved[source] = asset.get_path_name()
    receipt_path.write_text(json.dumps(saved, indent=2), encoding='utf-8')
    print('KAITLIN_WORLD_GARMENT_SAVED', asset.get_path_name(), flush=True)
    del asset, mesh, data, positions
    gc.collect()
    u.SystemLibrary.collect_garbage()
    completed += 1
    if completed >= 4:
        break
print('KAITLIN_GARMENT_BATCH', completed, 'saved;', len(saved), '/', len(manifest))
(WORK / (stage + '_status.json')).write_text(json.dumps({
    'remaining': len(manifest) - len(saved), 'complete': all(path in saved for path in manifest)}), encoding='utf-8')
