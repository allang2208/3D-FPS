"""Save the existing M16 meshes through the serialized UE Python bridge.

Run this file directly with that bridge, or UE's unattended Python commandlet.
It never starts an editor, PIE, renders, changes animation keys or shared rigs.
Every package save appends its receipt immediately, making a batch resumable.
"""
import hashlib
import json
import shutil
from pathlib import Path

import unreal as u

P = Path(u.Paths.project_dir()).resolve()
O = Path(__file__).resolve().parent
G, Q = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries
E = u.EditorAssetLibrary
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
RECEIPT = O / 'installed.json'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def disk(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def persist(saved):
    temporary = RECEIPT.with_suffix('.next.json')
    temporary.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(RECEIPT)

def source_mesh(asset, patch):
    dm, result = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if result != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read M16 source model: ' + patch['source'])
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    if patch['arm_ids'] is not None:
        ids = sorted({v for i, triangle in enumerate(triangles)
            if u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] in patch['arm_ids']
            for v in (triangle.x, triangle.y, triangle.z)})
    else:
        _, positions, _ = Q.get_all_vertex_positions(dm, False)
        ids = list(range(len(u.GeometryScript_List.convert_vector_list_to_array(positions))))
    if len(ids) != patch['vertex_count']:
        raise RuntimeError('Preserve changed vertex mapping: ' + patch['source'])
    return dm, triangles, ids

def main():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Finish PIE before saving the M16 wrist binding')
    manifest = read(O / 'Authored/authoring.json')
    if sha(manifest['reference']) != manifest['reference_sha256']:
        raise RuntimeError('Wrist author reference changed after production')
    bind = read(manifest['reference'])
    saved = read(RECEIPT) if RECEIPT.exists() else {}
    dirty = {package.get_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    config = read(manifest['configuration'])
    for scope in manifest['cuff_scope']:
        if config['items'][scope['item']]['rig_meshes']['M16'] != scope['source']:
            raise RuntimeError('Preserve changed outfit configuration: ' + scope['item'])
    patches = []
    # All dirty/hash/source-position conditions precede this batch's first edit.
    for entry in manifest['patches']:
        if sha(entry['patch']) != entry['patch_sha256']:
            raise RuntimeError('Wrist geometry author patch changed: ' + entry['source'])
        patch = read(entry['patch'])
        path = patch['source']
        if path.split('.')[0] in dirty:
            raise RuntimeError('Preserve unsaved asset: ' + path)
        expected = saved.get(path, {}).get('after_sha256', patch['source_sha256'])
        if sha(disk(path)) != expected:
            raise RuntimeError('Preserve M16 package changed since authoring: ' + path)
        if path in saved:
            continue
        asset = u.load_asset(path)
        if not asset:
            raise RuntimeError('Missing existing M16 mesh: ' + path)
        if asset.skeleton.get_path_name().split('.')[0] in dirty:
            raise RuntimeError('Preserve unsaved shared skeleton: ' + asset.skeleton.get_path_name())
        dm, triangles, ids = source_mesh(asset, patch)
        _, positions, _ = Q.get_all_vertex_positions(dm, False)
        positions = u.GeometryScript_List.convert_vector_list_to_array(positions)
        for edit in patch['vertex_edits']:
            current = positions[ids[edit['index']]]
            original = edit['original']
            if max(abs(value - expected_value) for value, expected_value in
                   zip((current.x, current.y, current.z), original)) > .0005:
                raise RuntimeError('Preserve source surface differing from author input: ' + path)
        patches.append((asset, patch, entry))
    for asset, patch, entry in patches:
        path = patch['source']
        backup = O / 'Before/Packages' / disk(path).relative_to(P / 'Content')
        backup.parent.mkdir(parents=True, exist_ok=True)
        backups = []
        for suffix in ('.uasset', '.uexp', '.ubulk', '.uptnl'):
            original = disk(path).with_suffix(suffix)
            if original.exists():
                destination = backup.with_suffix(suffix)
                if not destination.exists():
                    shutil.copy2(original, destination)
                backups.append(str(destination))
        skeleton_path = asset.skeleton.get_path_name()
        skeleton_hash = sha(disk(skeleton_path))
        before_materials = [(str(slot.material_slot_name),
            slot.material_interface.get_path_name() if slot.material_interface else None)
            for slot in asset.materials]
        modifier = u.SkeletonModifier()
        if not modifier.set_skeletal_mesh(asset):
            raise RuntimeError('Cannot load native mesh reference: ' + path)
        names, transforms = [], []
        for bone in bind['local_transforms']:
            names.append(bone['name'])
            transform = u.Transform()
            transform.translation = u.Vector(*bone['translation'])
            transform.rotation = u.Quat(*bone['rotation_xyzw'])
            transform.scale3d = u.Vector(*bone['scale'])
            transforms.append(transform)
        if not modifier.set_bones_transforms(names, transforms, True):
            raise RuntimeError('Cannot copy common M4 V7 wrist mesh reference: ' + path)
        if not modifier.commit_skeleton_to_skeletal_mesh():
            raise RuntimeError('Cannot rebuild inverse wrist reference matrices: ' + path)
        dm, triangles, ids = source_mesh(asset, patch)
        moved = set()
        for edit in patch['vertex_edits']:
            index = ids[edit['index']]
            _, valid = u.GeometryScript_MeshEdits.set_vertex_position(dm, index,
                u.Vector(*edit['position']), True)
            if not valid:
                raise RuntimeError('Cannot author existing M16 vertex: ' + str(index))
            moved.add(index)
        affected = [i for i, triangle in enumerate(triangles)
                    if any(v in moved for v in (triangle.x, triangle.y, triangle.z))]
        _, selection = u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(
            dm, affected, u.GeometryScriptMeshSelectionType.TRIANGLES)
        u.GeometryScript_Normals.recompute_normals_for_mesh_selection(
            dm, selection, u.GeometryScriptCalculateNormalsOptions())
        options = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=False,
            enable_recompute_normals=False, enable_recompute_tangents=True,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _, outcome = G.copy_mesh_to_skeletal_mesh(dm, asset, options, u.GeometryScriptMeshWriteLOD())
        if outcome != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot save matching wrist geometry: ' + path)
        lod_count = S.get_lod_count(asset)
        if lod_count > 1 and not S.regenerate_lod(asset, lod_count, True, False):
            raise RuntimeError('Cannot rebuild existing companion LODs: ' + path)
        E.set_metadata_tag(asset, 'M16CommonLeftWristBind',
            '20261002; common M4 V7 wrist mesh bind; neutral nineteen digits retained; native lengths and scales')
        if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()], False)
                or E.save_loaded_asset(asset, False)):
            raise RuntimeError('Cannot save M16 wrist package: ' + path)
        saved[path] = dict(before_sha256=patch['source_sha256'],
            after_sha256=sha(disk(path)), backup=str(backup), backups=backups,
            edited_vertex_count=len(moved), retained_digit_reference_count=19,
            changed_local_reference_bones=entry.get('changed_local_reference_bones', ['hand_l']),
            saved_reference_bones=names, skeleton=skeleton_path,
            skeleton_sha256=skeleton_hash, material_slots=before_materials,
            native_length_scale_hierarchy_preserved=True, weights_preserved=True,
            runtime_twist_compensation=False, animation_assets_changed=False,
            runtime_tested=False, rendered=False)
        persist(saved)
        u.log('CLOVEN_M16_COMMON_WRIST_BIND_SAVED ' + path)
    u.log('CLOVEN_M16_COMMON_WRIST_BIND_INSTALL_COMPLETE ' + str(len(saved)))

main()
