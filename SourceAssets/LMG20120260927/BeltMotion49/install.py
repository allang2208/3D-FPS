"""Install rigid feed cells only; preserve the live body, materials and actions."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
PROJECT = O.parents[2]
P = '/Game/Weapons/LMG201/BeltMotion49'
BODY = '/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
layout = json.loads((O / 'layout.json').read_text())
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
G = u.GeometryScript_AssetUtils
M = u.GeometryScript_Materials
L = u.GeometryScript_List
Ed = u.GeometryScript_MeshEdits
receipt_path = O / 'delivery.json'
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {
    'status': 'installing', 'backups': {}, 'saved': {}, 'runtime_tested': False,
    'animations_modified': False, 'native_code_modified': True}


def record():
    receipt_path.write_text(json.dumps(receipt, indent=2))


def file(asset):
    return PROJECT / 'Content' / (asset.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(asset):
    return hashlib.sha256(file(asset).read_bytes()).hexdigest()


def load(asset):
    result = u.load_asset(asset)
    if not result:
        raise RuntimeError('Missing ' + asset)
    return result


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def dynamic(asset):
    dm, status = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read ' + asset.get_path_name())
    return dm


expected = receipt['saved'].get(BODY, {}).get('sha256', layout['source_body_sha256'])
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if BODY in dirty or sha(BODY) != expected:
    raise RuntimeError('Concurrent or unsaved body retained: ' + BODY)
digest = hashlib.sha256(Path(layout['fbx']).read_bytes()).hexdigest()
body = load(BODY)
lookup = {str(s.material_slot_name): s.material_interface for s in body.materials}
source_path = P + '/Parts/SK_Belt49_' + digest[:8]
part = u.load_asset(source_path)
if not part:
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal = True
    opt.import_mesh = True
    opt.import_animations = opt.import_materials = opt.import_textures = False
    opt.create_physics_asset = False
    opt.skeleton = body.skeleton
    data = opt.skeletal_mesh_import_data
    data.set_editor_property('update_skeleton_reference_pose', False)
    data.set_editor_property('use_t0_as_ref_pose', False)
    data.set_editor_property('preserve_smoothing_groups', True)
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
    data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    task = u.AssetImportTask()
    task.filename = layout['fbx']
    task.destination_path = P + '/Parts'
    task.destination_name = source_path.rsplit('/', 1)[1]
    task.factory = u.FbxFactory()
    task.options = opt
    task.automated = True
    task.save = False
    flag = 'Interchange.FeatureFlags.Import.FBX'
    prior = u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    try:
        A.import_asset_tasks([task])
    finally:
        u.SystemLibrary.execute_console_command(None, flag + ' ' + str(prior))
    part = load(source_path)
part_slots = [s.copy() for s in part.materials]
for slot in part_slots:
    name = str(slot.material_slot_name)
    slot.material_interface = lookup[layout['old_slots'][layout['slots'].index(name)]]
part.materials = part_slots
save(part)

if receipt['saved'].get(BODY, {}).get('source_sha256') != digest:
    native, added = dynamic(body), dynamic(part)
    slots = [s.copy() for s in body.materials]
    _, triangles, _ = u.GeometryScript_MeshQueries.get_all_triangle_indices(native, False)
    remove = []
    for ti in range(len(L.convert_triangle_list_to_array(triangles))):
        mid, valid = M.get_triangle_material_id(native, ti)
        if valid and str(slots[mid].material_slot_name) in layout['old_slots']:
            remove.append(ti)
    if not remove:
        raise RuntimeError('Current cloth belt was not found; body retained')
    Ed.delete_triangles_from_mesh(native,
        L.convert_array_to_index_list(remove, u.GeometryScriptIndexType.TRIANGLE), True)
    u.GeometryScript_BoneWeights.copy_bones_from_mesh(native, added,
        u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
    names = {str(s.material_slot_name): i for i, s in enumerate(slots)}
    for slot in part_slots:
        name = str(slot.material_slot_name)
        if name not in names:
            names[name] = len(slots)
            slots.append(slot.copy())
    for i in range(len(part_slots)):
        M.remap_material_i_ds(added, i, 1000 + i)
    for i, slot in enumerate(part_slots):
        M.remap_material_i_ds(added, 1000 + i, names[str(slot.material_slot_name)])
    Ed.append_mesh(native, added, u.Transform(), True)
    if BODY not in receipt['backups']:
        backup = O / 'Before' / file(BODY).relative_to(PROJECT / 'Content')
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file(BODY), backup)
        receipt['backups'][BODY] = {'file': str(backup), 'sha256': sha(BODY)}
        record()
    options = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[s.material_interface for s in slots],
        new_material_slot_names=[s.material_slot_name for s in slots],
        enable_recompute_normals=False, enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, status = G.copy_mesh_to_skeletal_mesh(native, body, options, u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot write the assembled body')
    body.materials = slots
    E.set_metadata_tag(body, '201BeltMotionRevision', 'BeltMotion49: seven closed rigid cells; PKM feed timing and constrained damping')
    E.set_metadata_tag(body, '201BeltMotionSource', str(O / 'LMG201_BeltMotion49.blend'))
    save(body)
    receipt['saved'][BODY] = {'sha256': sha(BODY), 'source_sha256': digest,
        'removed_old_belt_triangles': len(remove), 'slots': layout['slots']}
    record()

receipt['saved'][source_path] = {'sha256': sha(source_path), 'source_sha256': digest}
bindings = {str(s.material_slot_name): s.material_interface.get_path_name() if s.material_interface else None
    for s in body.materials}
(O / 'bindings.json').write_text(json.dumps({BODY: bindings}, indent=2))
manifest = O.parent / 'Material21/bindings.json'
mapping = json.loads(manifest.read_text())
mapping['meshes'][body.get_path_name()] = bindings
mapping['current_belt_motion_revision'] = 'BeltMotion49'
manifest.write_text(json.dumps(mapping, indent=2))
receipt.update(status='current_belt49_saved', source=str(O / 'LMG201_BeltMotion49.blend'),
    material_assets_changed=False, skeleton_changed=False, rendered_acceptance=False)
record()
print('BELT49_CURRENT_SAVED', BODY, flush=True)
