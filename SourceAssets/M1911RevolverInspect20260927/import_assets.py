"""Save the two new M1911 clips; the original revolver asset is left intact."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
folder = '/Game/Weapons/M1911/RevolverInspect20260927/Animations'
editor = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
subsystem = u.get_editor_subsystem(u.UnrealEditorSubsystem)
# This batch creates only new animation packages, rejects existing destinations,
# and never replaces a loaded animation/mesh or changes the skeleton reference
# pose. It does not need to end the user's current play session.
u.SystemLibrary.execute_console_command(subsystem.get_editor_world() if subsystem else None, 'Interchange.FeatureFlags.Import.FBX 0')
mesh = u.load_asset('/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny')
original = u.load_asset('/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_inspect')
if not mesh or not original:
    raise RuntimeError('The original revolver inspect or native M1911 mesh is missing.')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt_path = P / 'import.json'
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {
    'assets': [], 'original_revolver': original.get_path_name(), 'testing': 'Not performed; user testing'}
for kind, info in json.loads((P / 'authoring.json').read_text())['clips'].items():
    name = 'A_M1911_' + kind; path = folder + '/' + name
    if path + '.' + name in receipt['assets']: continue
    if editor.does_asset_exist(path): raise RuntimeError('Unrecorded target preserved: ' + path)
    opts = u.FbxImportUI(); opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    opts.import_mesh = False; opts.import_animations = True; opts.import_materials = False; opts.import_textures = False
    opts.skeleton = mesh.skeleton
    opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    opts.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
    task = u.AssetImportTask(); task.filename = info['fbx']; task.destination_path = folder; task.destination_name = name
    task.automated = True; task.replace_existing = False; task.save = False; task.options = opts
    tools.import_asset_tasks([task]); clip = u.load_asset(path)
    if not clip: raise RuntimeError('Import failed ' + path)
    if compression: clip.set_editor_property('bone_compression_settings', compression)
    editor.set_metadata_tag(clip, 'M1911Inspect.Source', original.get_path_name())
    if not editor.save_loaded_asset(clip, False): raise RuntimeError('Save failed ' + path)
    receipt['assets'].append(clip.get_path_name())
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf8')
u.log('M1911_REVOLVER_INSPECT_SAVED ' + str(len(receipt['assets'])))
