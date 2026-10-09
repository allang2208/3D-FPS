"""Import and save the continuous normal reload; preserve all existing assets."""
import unreal as u, json, hashlib
from pathlib import Path

O = Path(__file__).parent
ROOT = '/Game/Weapons/Super90/Cransh20261006'
name = 'A_Super90_reload_continuous'
source = O / (name + '.fbx')
mesh = u.load_asset(ROOT + '/SK_Super90_V7')
if not mesh:
    raise RuntimeError('Missing Super90 native mesh')
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.skeleton = mesh.skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 60)
    task = u.AssetImportTask()
    task.filename = str(source)
    task.destination_path = ROOT + '/Animations'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    task.options = options
    task.factory = u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Continuous reload FBX import failed')
    asset = u.load_asset(ROOT + '/Animations/' + name)
    if not asset:
        raise RuntimeError('Missing imported continuous reload')
    asset.set_editor_property('bone_compression_settings', u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    u.EditorAssetLibrary.set_metadata_tag(asset, 'Super90SourceSHA256', hashlib.sha256(source.read_bytes()).hexdigest())
    u.EditorAssetLibrary.set_metadata_tag(asset, 'Super90ContinuousReload', '20261007: closed bolt, seven canted feeds, single return')
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Continuous reload package save failed')
    (O / 'import_receipt.json').write_text(json.dumps({'animation_saved': asset.get_path_name(),
        'completed': True, 'runtime_tested': False}, indent=2), encoding='utf-8')
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))
print('SUPER90_CONTINUOUS_RELOAD_SAVED', asset.get_path_name())
