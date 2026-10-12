"""Restore the mounted shell's source material identity without reimporting FBX."""
import collections, hashlib, json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = O.parents[1]
PATH = '/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7'
file = P / 'Content/Weapons/Super90/Cransh20261006/SK_Super90_V7.uasset'
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Stop PIE before saving the Super90 shell material repair.')
if PATH in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Keep the unsaved Super90 mesh; resolve its edits before applying this patch.')
before_sha = hashlib.sha256(file.read_bytes()).hexdigest()
if before_sha != '26d8abe2258ae884c0818f9acb5a20a6b6ab5841bd343fd526484094f50cd58b':
    raise RuntimeError('Super90 mesh changed after the source face comparison; preserve the newer asset.')
mesh = u.load_asset(PATH)
slots = [s.copy() for s in mesh.materials]
if str(slots[7].material_slot_name) != 'S90_MovingSteel' or str(slots[12].material_slot_name) != '12gauge_mounted':
    raise RuntimeError('Unexpected source material identities.')
G = u.GeometryScript_AssetUtils
dm, status = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot load existing Super90 source geometry.')
_, triangles, _ = u.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
ids = [u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] for i in range(len(triangles))]
counts = collections.Counter(ids)
if counts[7] != 830 or counts[12] != 1903:
    raise RuntimeError('The compared shell/moving-part polygon groups changed.')
# The original Cransh face correspondence identifies group 7 as the 830-face
# root-mounted cartridge and group 12 as the bolt/loading-gate/trigger steel.
# Their UVs are already correct. Assign them to the matching existing slots.
for i, material_id in enumerate(ids):
    if material_id in (7, 12):
        u.GeometryScript_Materials.set_triangle_material_id(dm, i, 12 if material_id == 7 else 7)
options = u.GeometryScriptCopyMeshToAssetOptions(
    enable_recompute_normals=False, enable_recompute_tangents=False,
    use_original_vertex_order=True, replace_materials=True,
    new_materials=[s.material_interface for s in slots],
    new_material_slot_names=[s.get_editor_property('imported_material_slot_name') for s in slots],
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_, status = G.copy_mesh_to_skeletal_mesh(dm, mesh, options, u.GeometryScriptMeshWriteLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Could not rebuild the corrected material section routing.')
# Keep the existing runtime slot labels, imported identities, UV streaming data,
# and material interfaces. Only polygon-group routing has changed.
mesh.set_editor_property('materials', slots)
u.EditorAssetLibrary.set_metadata_tag(mesh, 'Super90MountedShellMaterial',
    '20261012: mounted cartridge uses original red 12gauge atlas; moving steel uses WS1 steel; explicit source slot identities')
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('Could not save the Super90 shell material repair.')
receipt = {'saved': True, 'mesh': PATH, 'before_sha256': before_sha,
           'saved_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
           'mounted_shell_faces': 830, 'moving_steel_faces': 1903,
           'changes': {'7 -> 12': 'mounted red shell', '12 -> 7': 'moving gun steel'},
           'geometry_positions_edited': False, 'uvs_edited': False,
           'skin_weights_edited': False, 'animation_assets_edited': False,
           'textures_edited': False, 'runtime_tested': False}
(O / 'save_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('SUPER90_MOUNTED_SHELL_MATERIAL_SAVED', json.dumps(receipt))
