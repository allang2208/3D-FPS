"""Save only the authored proximal left-thumb skin-weight partition.

Existing GeometryScript source-LOD vertex mapping and native reference are
retained.  The root task owns execution through the serialized UE bridge or
background commandlet; this author never launches UE.
"""
import hashlib
import json
import shutil
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = Path(u.Paths.project_dir()).resolve()
G, Q, B = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_BoneWeights
E = u.EditorAssetLibrary
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
RECEIPT = HERE / 'installed.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package(source):
    return PROJECT / 'Content' / (source.split('.')[0].removeprefix('/Game/') + '.uasset')


def persist(saved):
    temp = RECEIPT.with_suffix('.next.json')
    temp.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(RECEIPT)


def source_mesh(asset, patch):
    dm, outcome = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Source model not available: ' + patch['source'])
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    if patch['arm_ids'] is not None:
        ids = sorted({v for i, t in enumerate(triangles)
            if u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] in patch['arm_ids']
            for v in (t.x, t.y, t.z)})
    else:
        _, positions, _ = Q.get_all_vertex_positions(dm, False)
        ids = list(range(len(u.GeometryScript_List.convert_vector_list_to_array(positions))))
    if len(ids) != patch['vertex_count']:
        raise RuntimeError('Preserve differing vertex mapping: ' + patch['source'])
    _, bones = B.get_all_bones_info(dm)
    names = {bone.index: str(bone.name) for bone in bones}
    return dm, ids, names


def main():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Finish PIE before saving wrist skin weights')
    manifest = read(HERE / 'Authored/authoring.json')
    saved = read(RECEIPT) if RECEIPT.exists() else {}
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    pending = []
    # These conditions protect the production inputs before the first edit.
    for entry in manifest['patches']:
        if digest(entry['patch']) != entry['patch_sha256']:
            raise RuntimeError('Preserve author patch differing from manifest')
        patch = read(entry['patch'])
        source = patch['source']
        expected = saved.get(source, {}).get('after_sha256', patch['source_sha256'])
        if source.split('.')[0] in dirty or digest(package(source)) != expected:
            raise RuntimeError('Preserve changed/unsaved source mesh: ' + source)
        if source in saved:
            continue
        asset = u.load_asset(source)
        if not asset:
            raise RuntimeError('Missing source mesh: ' + source)
        dm, ids, names = source_mesh(asset, patch)
        _, positions, _ = Q.get_all_vertex_positions(dm, False)
        positions = u.GeometryScript_List.convert_vector_list_to_array(positions)
        for edit in patch['vertex_edits']:
            index = ids[edit['index']]
            p = positions[index]
            if max(abs(a-b) for a,b in zip((p.x,p.y,p.z),edit['original_position'])) > .0005:
                raise RuntimeError('Preserve differing source surface: ' + source)
            _, current, valid = B.get_vertex_bone_weights(dm, index)
            if not valid:
                raise RuntimeError('Unavailable source skin vertex: ' + source)
            current = {names[w.bone_index]: w.weight for w in current if w.weight > 0}
            old = edit['original_weights']
            if max((abs(current.get(n,0)-old.get(n,0)) for n in current.keys()|old.keys()), default=0) > .001:
                raise RuntimeError('Preserve differing source skin weights: ' + source)
        pending.append((asset, dm, ids, names, patch))
    for asset, dm, ids, names, patch in pending:
        source = patch['source']
        backup = HERE / 'Before/Packages' / package(source).relative_to(PROJECT / 'Content')
        backup.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ('.uasset','.uexp','.ubulk','.uptnl'):
            original = package(source).with_suffix(suffix)
            destination = backup.with_suffix(suffix)
            if original.exists() and not destination.exists():
                shutil.copy2(original,destination)
        by_name = {n:i for i,n in names.items()}
        for edit in patch['vertex_edits']:
            _, valid = B.set_vertex_bone_weights(dm, ids[edit['index']],
                [u.GeometryScriptBoneWeight(bone_index=by_name[n],weight=w)
                 for n,w in edit['weights'].items()])
            if not valid:
                raise RuntimeError('Cannot write proximal thumb weight partition: ' + source)
        options = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=False,
            enable_recompute_normals=False,enable_recompute_tangents=False,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _, outcome = G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
        if outcome != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot save authored skin weights: ' + source)
        lod_count = S.get_lod_count(asset)
        if lod_count > 1 and not S.regenerate_lod(asset,lod_count,True,False):
            raise RuntimeError('Cannot rebuild existing companion LODs: ' + source)
        E.set_metadata_tag(asset,'DoorGuardProximalThumbPartition',
            '20261002 V8; proximal thumb spill -> hand_l; geometry/native reference preserved')
        if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False)
                or E.save_loaded_asset(asset,False)):
            raise RuntimeError('Cannot save source package: ' + source)
        saved[source] = dict(before_sha256=patch['source_sha256'],
            after_sha256=digest(package(source)),backup=str(backup),
            edited_weight_vertex_count=len(patch['vertex_edits']),
            positions_changed=False,reference_bones_changed=False,
            shared_skeleton_changed=False,animation_assets_changed=False,
            runtime_tested=False,rendered=False)
        persist(saved)
        u.log('DOOR_GUARD_WRIST_WEIGHT_PARTITION_SAVED ' + source)
    u.log('DOOR_GUARD_WRIST_WEIGHT_PARTITION_COMPLETE ' + str(len(saved)))


main()
