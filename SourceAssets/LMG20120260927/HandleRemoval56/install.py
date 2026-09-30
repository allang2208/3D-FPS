"""Remove the rejected H54/M55 carry assembly and the hanging block's end cap.

The end cap is a separate F37_Interior component, so deleting H39_Receiver
alone in H54 left it behind. Keep all other surfaces and bone indices intact.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = O.parents[2]
BODY = '/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
CANDIDATE = '/Game/Weapons/LMG201/HandleRemoval56/SK_LMG201_HandleRemoval56_Candidate'
source = json.loads((O / 'source.json').read_text())
E = u.EditorAssetLibrary
G = u.GeometryScript_AssetUtils
Q = u.GeometryScript_MeshQueries
M = u.GeometryScript_Materials
B = u.GeometryScript_BoneWeights
L = u.GeometryScript_List


def file(path):
    return P / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def sha(path):
    return hashlib.sha256(file(path).read_bytes()).hexdigest()


def preflight():
    if sha(BODY) != source['sha256']:
        raise RuntimeError('Body changed since capture; current work retained')
    if BODY in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Body has unsaved edits; current work retained')
    sub = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if sub and sub.get_game_world():
        raise RuntimeError('PIE is active; no asset modified')


def copy_to(dm, asset, slots):
    opt = u.GeometryScriptCopyMeshToAssetOptions(
        replace_materials=True,
        new_materials=[s.material_interface for s in slots],
        new_material_slot_names=[s.material_slot_name for s in slots],
        enable_recompute_normals=False, enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, status = G.copy_mesh_to_skeletal_mesh(dm, asset, opt, u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Native mesh write failed: ' + asset.get_path_name())
    asset.materials = [s.copy() for s in slots]


def save(asset):
    E.set_metadata_tag(asset, '201CarryHandleRevision', 'HandleRemoval56: H54/M55 assembly removed at user request')
    E.set_metadata_tag(asset, '201CarryHandleSource', 'Retired; see SourceAssets/LMG20120260927/HandleRemoval56/README.md')
    E.set_metadata_tag(asset, '201UndersideCleanup', 'H56: remove 49-face F37 end cap left by H54 block removal')
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())


preflight()
if E.does_asset_exist(CANDIDATE):
    raise RuntimeError('Existing H56 candidate retained; inspect receipt before retry')
body = u.load_asset(BODY)
slots = [s.copy() for s in body.materials]
names = [str(s.material_slot_name) for s in slots]
dm, status = G.copy_mesh_from_skeletal_mesh(body, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot read current body')
_, bones = B.get_all_bones_info(dm)
root = next(b.world_transform for b in bones if str(b.name) == 'WPN_root')
_, tl, _ = Q.get_all_triangle_indices(dm, False)
triangles = L.convert_triangle_list_to_array(tl)
carry_ids = []
cap_ids = []
position_cache = {}


def root_position(vi):
    if vi not in position_cache:
        p, valid = Q.get_vertex_position(dm, vi)
        if not valid:
            raise RuntimeError('Missing source vertex')
        position_cache[vi] = root.inverse_transform_location(p).to_tuple()
    return position_cache[vi]


for ti, t in enumerate(triangles):
    mid, valid = M.get_triangle_material_id(dm, ti)
    if not valid:
        continue
    name = names[mid]
    if name in ('M_LMG201_H54_CarryHandle_Polymer', 'M_LMG201_H54_CarryHandle_Coat'):
        carry_ids.append(ti)
    elif name == 'M_LMG201_F37_Interior':
        # The original block ended at this plane. Its orphan end cap is
        # below the receiver and wholly to its right; no receiver wall is cut.
        ps = [root_position(vi) for vi in (t.x, t.y, t.z)]
        if all(abs(y - .222510) < .000002 and
               -.032939 <= x <= -.015082 and
               -.035128 <= z <= -.000498 for x, y, z in ps):
            cap_ids.append(ti)

if len(carry_ids) != 4311 or len(cap_ids) != 49:
    raise RuntimeError('Source selection changed: carry=%d end_cap=%d; no asset modified' % (len(carry_ids), len(cap_ids)))
removals = carry_ids + cap_ids
(O / 'removals.json').write_text(json.dumps({
    'source_body_sha256': source['sha256'], 'carry_triangle_ids': carry_ids,
    'orphan_end_cap_triangle_ids': cap_ids, 'total_faces': len(removals)}, indent=2))
u.GeometryScript_MeshEdits.delete_triangles_from_mesh(
    dm, L.convert_array_to_index_list(removals, u.GeometryScriptIndexType.TRIANGLE), True)
candidate = E.duplicate_asset(BODY, CANDIDATE)
if not candidate:
    raise RuntimeError('Could not create H56 candidate')
copy_to(dm, candidate, slots)
save(candidate)
receipt = {
    'status': 'candidate_saved', 'source_body_sha256': source['sha256'],
    'candidate': CANDIDATE, 'candidate_sha256': sha(CANDIDATE),
    'removed_carry_handle_faces': len(carry_ids), 'removed_orphan_end_cap_faces': len(cap_ids),
    'unused_carry_bone_retained_for_index_stability': True,
    'animations_modified': False, 'materials_changed': False,
    'runtime_tested': False}
(O / 'delivery.json').write_text(json.dumps(receipt, indent=2))
print('H56_CANDIDATE_SAVED', flush=True)
preflight()
backup = O / 'Before' / file(BODY).relative_to(P / 'Content')
backup.parent.mkdir(parents=True, exist_ok=True)
if backup.exists():
    raise RuntimeError('Original H56 backup retained; no overwrite')
shutil.copy2(file(BODY), backup)
copy_to(dm, body, slots)
save(body)
receipt.update(status='current_body_saved', saved={BODY: {'sha256': sha(BODY)}}, backup=str(backup))
(O / 'delivery.json').write_text(json.dumps(receipt, indent=2))
bindings = {str(s.material_slot_name): s.material_interface.get_path_name() if s.material_interface else None for s in body.materials}
(O / 'bindings.json').write_text(json.dumps({body.get_path_name(): bindings}, indent=2))
manifest = O.parent / 'Material21/bindings.json'
data = json.loads(manifest.read_text())
data['meshes'][body.get_path_name()] = bindings
data['current_geometry_revision'] = 'HandleRemoval56'
data['current_carry_handle_revision'] = 'Removed56'
manifest.write_text(json.dumps(data, indent=2))
print('H56_CURRENT_SAVED', receipt['saved'], flush=True)
