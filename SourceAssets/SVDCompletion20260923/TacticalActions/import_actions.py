"""Import and save only the four authored SVD tactical actions."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/TacticalActions')
BASE = '/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations'
KEYS = ('sprint_enter', 'sprint_loop', 'sprint_exit', 'quick_melee')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop the active play session before importing SVD actions')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
targets = {BASE + '/A_SVD_' + key for key in KEYS}
targets.add('/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton')
if dirty.intersection(targets):
    raise RuntimeError('Unsaved target packages: ' + str(sorted(dirty.intersection(targets))))
skeleton = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton')
compression = u.load_asset('/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload').get_editor_property('bone_compression_settings')
tools = u.AssetToolsHelpers.get_asset_tools()
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
receipt = {'status': 'Importing', 'animations': {}, 'runtime_testing': 'Not performed'}
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    for key in KEYS:
        name = 'A_SVD_' + key
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh = False
        options.import_animations = True
        options.import_materials = False
        options.import_textures = False
        options.skeleton = skeleton
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
        task = u.AssetImportTask()
        task.filename = str(OUT.parent / 'Exports' / (name + '.fbx'))
        task.destination_path = BASE
        task.destination_name = name
        task.factory = u.FbxFactory()
        task.options = options
        task.automated = True
        task.replace_existing = True
        task.save = False
        tools.import_asset_tasks([task])
        path = BASE + '/' + name
        if not task.imported_object_paths:
            raise RuntimeError('No imported asset returned for ' + path)
        clip = u.load_asset(path)
        clip.set_editor_property('bone_compression_settings', compression)
        if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
            raise RuntimeError('Save failed: ' + path)
        receipt['animations'][key] = {'asset': clip.get_path_name(), 'saved': True,
                                      'duration': clip.get_play_length(), 'source': task.filename}
        (OUT / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        u.log('SVD_TACTICAL_IMPORTED ' + name)
    receipt['status'] = 'Imported and saved; user runtime testing pending'
    (OUT / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    u.log('SVD_TACTICAL_IMPORT_COMPLETE 4')
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))
