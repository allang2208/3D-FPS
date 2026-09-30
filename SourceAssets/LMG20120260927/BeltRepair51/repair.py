"""Repair Belt49's 100x mesh-space conversion and return-cell skin weights.

Run prepare.py then publish.py in separate headless UE commandlets. No animation,
material, reference skeleton, hand contact, or native gameplay code is changed.
"""
import collections
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
PROJECT = O.parents[2]
BODY = '/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
CANDIDATE = '/Game/Weapons/LMG201/BeltRepair51/SK_LMG201_BeltRepair51_Candidate'
EXPECTED = '491ed8ded129d95c847817394954266cc4720fd5e74c175a672bbde0b2b01b2f'
SLOT = 'M_LMG201_Cloth33__OldBelt_Belt49'
LAYOUT = json.loads((O.parent / 'BeltMotion49/layout.json').read_text())
E = u.EditorAssetLibrary
G = u.GeometryScript_AssetUtils
B = u.GeometryScript_BoneWeights
Q = u.GeometryScript_MeshQueries


def disk(path):
    return PROJECT / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def sha(path):
    return hashlib.sha256(disk(path).read_bytes()).hexdigest()


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing asset: ' + path)
    return asset


def read(asset):
    dm, status = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read ' + asset.get_path_name())
    return dm


def slots(asset):
    return [(str(s.material_slot_name), s.material_interface.get_path_name()
             if s.material_interface else None) for s in asset.materials]


def cells(dm, asset):
    _, bl = B.get_all_bones_info(dm)
    bones = {str(b.name): b for b in bl}
    names = {b.index: str(b.name) for b in bl}
    _, tl, _ = Q.get_all_triangle_indices(dm, False)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(tl)
    selected, other, counts = set(), set(), collections.Counter()
    for ti, t in enumerate(triangles):
        mid, valid = u.GeometryScript_Materials.get_triangle_material_id(dm, ti)
        if not valid:
            continue
        name = str(asset.materials[mid].material_slot_name)
        counts[name] += 1
        (selected if name == SLOT else other).update([t.x, t.y, t.z])
    if not selected or selected & other:
        raise RuntimeError('Belt section absent or shares vertices outside the repair')
    groups = collections.defaultdict(list)
    for vid in sorted(selected):
        p, valid = Q.get_vertex_position(dm, vid)
        _, ws, valid = B.get_vertex_bone_weights(dm, vid)
        influences = tuple(sorted(names[w.bone_index] for w in ws if w.weight > 0))
        groups[influences].append((vid, p))
    return groups, bones, dict(counts)


def inspect(dm, asset):
    groups, bones, counts = cells(dm, asset)
    result = {'cells': [], 'triangles_by_slot': counts}
    for i in range(7):
        name = 'LMG201_Belt_%02d' % i
        rows = groups.pop((name,), [])
        if not rows:
            raise RuntimeError('Rigid cell missing: ' + name)
        center = sum((p for _, p in rows), u.Vector()) / len(rows)
        local = bones[name].world_transform.inverse_transform_location(center)
        expected = u.Vector(*LAYOUT['centers_bone_local'][i])
        error_cm = (local - expected).length() * 100.
        if error_cm > .02:
            raise RuntimeError('Cell differs from authored contact: %s %.6f cm' % (name, error_cm))
        result['cells'].append({'bone': name, 'vertices': len(rows),
            'center_cm': list(center.to_tuple()), 'contact_error_cm': error_cm})
    if groups:
        raise RuntimeError('Residual cross-cell weights: ' + str(list(groups)))
    return result


def write(dm, asset, original_slots):
    options = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[s.material_interface for s in original_slots],
        new_material_slot_names=[s.material_slot_name for s in original_slots],
        enable_recompute_normals=False, enable_recompute_tangents=False,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, status = G.copy_mesh_to_skeletal_mesh(dm, asset, options, u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot write ' + asset.get_path_name())
    asset.materials = [s.copy() for s in original_slots]


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def preflight():
    if sha(BODY) != EXPECTED:
        raise RuntimeError('Current body changed; retain concurrent edit')
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if BODY in dirty:
        raise RuntimeError('Unsaved current body retained')


def prepare():
    preflight()
    body = load(BODY)
    dm = read(body)
    groups, bones, counts = cells(dm, body)
    mixed = ('LMG201_Belt_05', 'LMG201_Belt_06')
    expected_groups = {('LMG201_Belt_%02d' % i,) for i in range(6)} | {mixed}
    if set(groups) != expected_groups:
        raise RuntimeError('Source no longer has diagnosed Belt49 binding')
    repaired, rebound = 0, 0
    for key, rows in groups.items():
        for vid, p in rows:
            _, valid = u.GeometryScript_MeshEdits.set_vertex_position(dm, vid, p * .01, True)
            if not valid:
                raise RuntimeError('Invalid belt vertex')
            repaired += 1
            if key == mixed:
                _, valid = B.set_vertex_bone_weights(dm, vid,
                    [u.GeometryScriptBoneWeight(bone_index=bones['LMG201_Belt_06'].index, weight=1.)])
                if not valid:
                    raise RuntimeError('Cannot rebind return cell')
                rebound += 1
    expected = inspect(dm, body)
    if E.does_asset_exist(CANDIDATE):
        raise RuntimeError('Candidate already exists; do not overwrite unknown output')
    candidate = E.duplicate_asset(BODY, CANDIDATE)
    if not candidate:
        raise RuntimeError('Cannot create candidate')
    write(dm, candidate, [s.copy() for s in body.materials])
    result = inspect(read(candidate), candidate)
    if result['triangles_by_slot'] != counts or slots(candidate) != slots(body):
        raise RuntimeError('Candidate topology or material slots changed')
    E.set_metadata_tag(candidate, '201BeltRepairRevision', 'BeltRepair51: correct Belt49 mesh-space factor and rigid return cell')
    save(candidate)
    receipt = {'status': 'candidate_saved', 'source_sha256': EXPECTED,
        'candidate': CANDIDATE, 'candidate_sha256': sha(CANDIDATE),
        'scaled_vertices': repaired, 'rebound_return_vertices': rebound,
        'candidate_geometry': result, 'native_code_modified': False,
        'animations_modified': False, 'materials_modified': False,
        'runtime_tested': False, 'rendered_acceptance': False}
    (O / 'delivery.json').write_text(json.dumps(receipt, indent=2))
    print('BELT51_CANDIDATE_SAVED', repaired, rebound, flush=True)


def publish():
    preflight()
    receipt = json.loads((O / 'delivery.json').read_text())
    if sha(CANDIDATE) != receipt['candidate_sha256']:
        raise RuntimeError('Candidate changed; retained')
    candidate, body = load(CANDIDATE), load(BODY)
    dm = read(candidate)
    result = inspect(dm, candidate)
    if slots(candidate) != slots(body):
        raise RuntimeError('Material bindings changed')
    # This is a fresh process read of the saved candidate, before formal replacement.
    receipt['independent_candidate_read'] = result
    backup = O / 'Before' / disk(BODY).relative_to(PROJECT / 'Content')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        raise RuntimeError('Existing backup retained')
    shutil.copy2(disk(BODY), backup)
    receipt['backup'] = {'file': str(backup), 'sha256': EXPECTED}
    write(dm, body, [s.copy() for s in body.materials])
    inspect(read(body), body)
    E.set_metadata_tag(body, '201BeltRepairRevision', 'BeltRepair51: correct Belt49 mesh-space factor and rigid return cell')
    E.set_metadata_tag(body, '201BeltRepairSource', str(O / 'repair.py'))
    save(body)
    receipt.update(status='current_body_saved', saved={BODY: {'sha256': sha(BODY)}})
    (O / 'delivery.json').write_text(json.dumps(receipt, indent=2))
    print('BELT51_CURRENT_SAVED', BODY, receipt['saved'], flush=True)
