"""Reuse M4 V7's wrist mesh bind, rebuilding surfaces from their first source.

This production extends, and never rewrites, the existing nineteen-finger
NeutralBind production.  Source meshes keep their native M16 animation skeleton,
translations, scales, hierarchy, weights, UVs, material slots and mechanics.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
REPAIR = PROJECT / 'SourceAssets/M16Repair20261002'
NEUTRAL = REPAIR / 'NeutralBind'
V7 = PROJECT / 'SourceAssets/ModularOutfit20260925/BarePalmV7'
OUT = HERE / 'Authored'
spec = importlib.util.spec_from_file_location('prior_neutral_author', NEUTRAL / 'author_neutral_bind.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def package(path):
    return PROJECT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')

def changed(name):
    return name == 'hand_l' or prior.is_digit(name)

def indices(data):
    return [i for i, weights in enumerate(data['weights'])
            if any(changed(name) and weight > 0 for name, weight in weights.items())]

def reference(current, common):
    """Replace only hand_l local rotation; retained nineteen common digits."""
    current_world = {name: prior.matrix(bone) for name, bone in current.items()}
    common_world = {name: prior.matrix(bone) for name, bone in common.items()}
    parent_names = {bone['index']: name for name, bone in current.items()}
    common_parents = {bone['index']: name for name, bone in common.items()}
    target_world, records = {}, []
    for name, bone in sorted(current.items(), key=lambda item: item[1]['index']):
        parent = parent_names.get(bone['parent'])
        local = (np.linalg.inv(current_world[parent]) @ current_world[name]
                 if parent else current_world[name].copy())
        if changed(name):
            position, current_rotation, scale = prior.decompose(local)
            common_parent = common_parents.get(common[name]['parent'])
            common_local = (np.linalg.inv(common_world[common_parent]) @ common_world[name]
                            if common_parent else common_world[name])
            _, common_rotation, _ = prior.decompose(common_local)
            # All nineteen digit rotations remain the current neutral source.
            rotation = common_rotation if name == 'hand_l' else current_rotation
            local[:3, :3] = rotation.as_matrix() @ np.diag(scale)
            local[:3, 3] = position
            records.append(dict(name=name, index=bone['index'], parent=parent,
                translation=position.tolist(), rotation_xyzw=rotation.as_quat().tolist(),
                scale=scale.tolist(), old_rotation_xyzw=current_rotation.as_quat().tolist(),
                changed_this_production=(name == 'hand_l')))
        target_world[name] = target_world[parent] @ local if parent else local
    bones = {name: dict(index=bone['index'], parent=bone['parent'],
        position=target_world[name][:3, 3].tolist(), axes=target_world[name][:3, :3].T.tolist())
        for name, bone in current.items()}
    return current_world, target_world, bones, records

def baseline_current(input_path, data):
    positions = np.asarray(data['positions'], dtype=float).copy()
    neutral_patch = read(NEUTRAL / 'Authored' / (input_path.stem + '.position_patch.json'))
    for edit in neutral_patch['vertex_edits']:
        positions[edit['index']] = edit['position']
    return positions

def common_vertex_map(data, raw):
    # Imported UV seams may duplicate a point. Select the donor with the same
    # actual skin weights at the wrist as well as at all nineteen fingers.
    mapping = prior.common_vertex_map(data, raw)
    positions = np.asarray(data['positions'])
    tree = cKDTree(np.asarray(raw['positions']))
    for index in indices(data):
        weights = data['weights'][index]
        candidates = tree.query_ball_point(positions[index], .0001)
        def error(candidate):
            donor = raw['weights'][candidate]
            return sum(abs(weights.get(name, 0) - donor.get(name, 0))
                       for name in weights.keys() | donor.keys())
        selected = min(candidates, key=error)
        if error(selected) > .001:
            raise RuntimeError('Common V7 wrist skin correspondence changed')
        mapping[index] = selected
    return mapping

def core_patch(input_path, raw, old_transfers, new_transfers, installed):
    data = read(input_path)
    original = np.asarray(data['positions'], dtype=float)
    current = baseline_current(input_path, data)
    target = current.copy()
    changed_indices = indices(data)
    primary = input_path.stem in prior.PRIMARY
    correspondence = common_vertex_map(data, raw) if primary else None
    for index in changed_indices:
        weights = data['weights'][index]
        canonical = (np.asarray(raw['canonical_positions'][correspondence[index]]) if primary
                     else np.linalg.solve(prior.blended(weights, old_transfers),
                                          np.r_[original[index], 1.])[:3])
        target[index] = (prior.blended(weights, new_transfers) @ np.r_[canonical, 1.])[:3]
    source = data['path']
    expected = installed[source]['after_sha256']
    if sha(package(source)) != expected:
        raise RuntimeError('Current M16 package changed: ' + source)
    output = OUT / (input_path.stem + '.position_patch.json')
    patch = dict(schema='m16_common_v7_left_wrist_bind_positions_v1', source=source,
        source_sha256=expected, skeleton=data['skeleton'], arm_ids=data.get('arm_ids'),
        vertex_index_space=('sorted_used_vertices_of_exported_arm_materials'
                            if data.get('arm_ids') is not None else 'full_mesh_vertex_ids'),
        input=str(input_path.resolve()), input_sha256=sha(input_path),
        vertex_count=len(original), triangle_count=len(data.get('triangles', [])),
        edited_vertex_count=len(changed_indices),
        max_movement_cm=float(np.linalg.norm(target - current, axis=1).max(initial=0)),
        vertex_edits=[dict(index=int(index), original=current[index].tolist(),
                           baseline_uncompressed=original[index].tolist(),
                           position=target[index].tolist()) for index in changed_indices],
        method=('exact_common_v7_surface_new_native_wrist_and_neutral_digits' if primary else
                'recover_first_shell_from_original_native_lbs_then_bind_common_wrist_once'),
        retained_digit_source=str(NEUTRAL / 'Authored/left_digit_reference.json'),
        preserved=['weights', 'triangles', 'uvs', 'material_slots', 'gun_geometry',
                   'right_arm', 'native_local_translation', 'native_local_scale',
                   'hierarchy', 'shared_animation_skeleton', 'existing_animation_keys'])
    write(output, patch)
    return dict(source=source, source_sha256=expected, patch=str(output), patch_sha256=sha(output),
                edited_vertex_count=len(changed_indices), vertex_count=len(original),
                max_movement_cm=patch['max_movement_cm'], group='eight_existing_neutral_bind_meshes')

def rest_matrix(rest):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_quat(rest['q']).as_matrix() @ np.diag(rest['s'])
    result[:3, 3] = rest['p']
    return result

def cuff_patch(source_path, snapshot_path, new_world, common):
    """Only necessary existing hand-weighted cuffs; forearm-only vertices stay."""
    data = read(snapshot_path)
    before = np.asarray(data['positions'])
    selected = indices(data)
    old_world = {name: rest_matrix(rest) for name, rest in data['rest'].items()}
    old_transfers = {name: matrix @ np.linalg.inv(prior.matrix(common[name]))
                     for name, matrix in old_world.items() if name in common}
    target_transfers = {name: new_world[name] @ np.linalg.inv(prior.matrix(common[name]))
                        for name in old_transfers}
    edits = []
    for index in selected:
        weights = data['weights'][index]
        first_canonical = np.linalg.solve(prior.blended(weights, old_transfers),
                                          np.r_[before[index], 1.])[:3]
        position = (prior.blended(weights, target_transfers) @ np.r_[first_canonical, 1.])[:3]
        edits.append(dict(index=index, original=before[index].tolist(), position=position.tolist()))
    output = OUT / (source_path.rsplit('/', 1)[-1].split('.')[0] + '.position_patch.json')
    expected = sha(package(source_path))
    patch = dict(schema='m16_common_wrist_existing_hand_weighted_cuff_v1', source=source_path,
        source_sha256=expected, input=str(snapshot_path.resolve()), input_sha256=sha(snapshot_path),
        vertex_count=len(before), triangle_count=len(data['triangles']), arm_ids=None,
        vertex_index_space='full_mesh_vertex_ids', edited_vertex_count=len(edits),
        max_movement_cm=max((float(np.linalg.norm(np.asarray(e['position']) - e['original']))
                             for e in edits), default=0.), vertex_edits=edits,
        method='recover_existing_native_cuff_once_then_common_wrist_bind',
        preserved=['forearm_only_vertices', 'weights', 'uvs', 'cuff_detail', 'lining',
                   'material_slots', 'native_translation_scale_hierarchy', 'lod_policy'])
    write(output, patch)
    return dict(source=source_path, source_sha256=expected, patch=str(output), patch_sha256=sha(output),
                edited_vertex_count=len(edits), vertex_count=len(before),
                max_movement_cm=patch['max_movement_cm'], group='necessary_hand_weighted_cuff',
                changed_local_reference_bones=[name for name in common if changed(name)])

def main():
    common_path = V7 / 'M4_original.json'
    raw_path = V7 / 'Authored/M16.json'
    current_path = NEUTRAL / 'NativeSources/M16.json'
    common = read(common_path)['bones']
    current = read(current_path)['bones']
    original = read(REPAIR / 'Input/AcceptedM16V7.json')['bones']
    raw = read(raw_path)
    _, new_world, bones, records = reference(current, common)
    old_transfers = prior.transfer({name: prior.matrix(bone) for name, bone in original.items()}, common)
    new_transfers = prior.transfer(new_world, common)
    reference_path = OUT / 'left_wrist_reference.json'
    write(reference_path, dict(schema='m16_common_m4_v7_wrist_reference_v1',
        current_native_source=str(current_path), current_native_sha256=sha(current_path),
        canonical=str(common_path), canonical_sha256=sha(common_path),
        retained_neutral_digits=str(NEUTRAL / 'Authored/left_digit_reference.json'),
        changed_local_reference_bones=['hand_l'], local_transforms=records, bones=bones,
        skeleton_asset_reference_unchanged=True, runtime_twist_compensation=False))
    installed = read(NEUTRAL / 'installed.json')
    inputs = [REPAIR / ('Input/' + name + '.json') for name in prior.PRIMARY]
    inputs.extend(sorted((REPAIR / 'Input/Outfits').glob('*M16*.json')))
    patches = [core_patch(path, raw, old_transfers, new_transfers, installed) for path in inputs]
    config_path = PROJECT / 'Content/ColdSteelData/modular_outfits.json'
    config = read(config_path)
    cuffs = [
        ('ue_field_sweater', PROJECT / 'SourceAssets/FieldSweaterNativeFamily20260930/Saved/M16/source.json'),
        ('ue_chainmail_shirt', PROJECT / 'SourceAssets/ChainmailCameraClearance20260929/M16/source.json'),
    ]
    cuff_scope = []
    for item, snapshot in cuffs:
        source = config['items'][item]['rig_meshes']['M16']
        if read(snapshot)['source'] != source:
            raise RuntimeError('Active sleeve differs from retained source: ' + item)
        entry = cuff_patch(source, snapshot, new_world, common)
        patches.append(entry)
        cuff_scope.append(dict(item=item, source=source, hand_or_digit_weighted_vertices=entry['edited_vertex_count']))
    charcoal_snapshot = PROJECT / 'SourceAssets/CharcoalCameraRepair20260930/Saved/M16/source.json'
    charcoal = read(charcoal_snapshot)
    if indices(charcoal):
        raise RuntimeError('Charcoal sleeve unexpectedly includes left wrist weights')
    cuff_scope.append(dict(item='ue_field_sweater_charcoal',
        source=config['items']['ue_field_sweater_charcoal']['rig_meshes']['M16'],
        hand_or_digit_weighted_vertices=0, action='unchanged; no wrist/hand/digit weighted geometry'))
    editable = dict(raw)
    positions = np.asarray(raw['positions']).copy()
    selected = indices(raw)
    for index in selected:
        positions[index] = (prior.blended(raw['weights'][index], new_transfers) @
                            np.r_[raw['canonical_positions'][index], 1.])[:3]
    editable['positions'] = positions.tolist()
    prior.update_normals(editable, positions, selected)
    editable['contract'] += '; left wrist mesh bind copied from common M4 V7; nineteen neutral digit refs retained'
    editable['common_left_wrist_bind'] = dict(changed_local_reference_bones=['hand_l'],
        retained_neutral_digit_count=19, native_translation_scale_hierarchy_preserved=True,
        animation_local_keys_unchanged=True)
    editable_path = OUT / 'M16_BareArmsV7_CommonWrist_Editable.json'
    write(editable_path, editable)
    native_path = HERE / 'NativeSources/M16.json'
    write(native_path, dict(bones=bones))
    write(HERE / 'manifest.json', [dict(profile='M16', authored=str(editable_path))])
    manifest = dict(schema='m16_common_m4_v7_wrist_authoring_v1',
        reference=str(reference_path), reference_sha256=sha(reference_path),
        raw_surface_source=str(raw_path), raw_surface_sha256=sha(raw_path),
        canonical_source=str(common_path), canonical_sha256=sha(common_path),
        retained_neutral_bind_production=str(NEUTRAL), patches=patches,
        cuff_scope=cuff_scope, configuration=str(config_path),
        editable=dict(source=str(editable_path), source_sha256=sha(editable_path),
                      native_reference=str(native_path), native_reference_sha256=sha(native_path)),
        native_animation_asset_changes=False, shared_skeleton_changes=False,
        native_length_scale_changes=False, runtime_tested=False, rendered=False,
        editor_imported=False, production_status='authored; awaiting existing UE bridge or commandlet save')
    write(OUT / 'authoring.json', manifest)
    for entry in patches:
        print('M16_COMMON_WRIST_AUTHORED', entry['source'], entry['edited_vertex_count'], flush=True)
    print('M16_COMMON_WRIST_AUTHOR_COMPLETE', len(patches), flush=True)

if __name__ == '__main__':
    main()
