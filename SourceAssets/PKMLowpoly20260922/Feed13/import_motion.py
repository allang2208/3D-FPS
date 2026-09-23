"""Import only the two PKM firing animations; keep mesh and reload assets."""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
P = '/Game/Weapons/PKMLowpoly20260922'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before PKM firing animation import and saving')
mesh = u.load_asset(P + '/SK_PKM_Manny')
if not mesh:
    raise RuntimeError('PKM geometry is required')
source = json.loads((O / 'authoring.json').read_text(encoding='utf-8'))
report = {}
A = u.AssetToolsHelpers.get_asset_tools()
for key in source['clips']:
    name = 'A_PKM_' + key
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    opt.skeleton = mesh.skeleton
    opt.import_mesh = False
    opt.import_animations = True
    opt.import_materials = False
    opt.import_textures = False
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate', source['export_fps'])
    task = u.AssetImportTask()
    task.filename = str(O / 'Exports' / (name + '.fbx'))
    task.destination_path = P + '/Animations'
    task.destination_name = name
    task.options = opt
    task.factory = u.FbxFactory()
    task.automated = True
    task.replace_existing = True
    task.save = True
    flag = 'Interchange.FeatureFlags.Import.FBX'
    prior = u.SystemLibrary.get_console_variable_int_value(flag)
    try:
        u.SystemLibrary.execute_console_command(None, flag + ' 0')
        A.import_asset_tasks([task])
    finally:
        u.SystemLibrary.execute_console_command(None, flag + ' ' + str(prior))
    clip = u.load_asset(task.destination_path + '/' + name)
    if not task.imported_object_paths or not clip:
        raise RuntimeError('Animation import failed: ' + name)
    clip.set_editor_property('bone_compression_settings', u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
        raise RuntimeError('Animation save failed: ' + name)
    report[key] = {'asset': clip.get_path_name(), 'seconds': clip.get_play_length()}
    (O / 'motion_import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('PKM13 firing feed clips saved. No PIE or runtime test performed.')
