import json, shutil
from pathlib import Path
import unreal as u

P = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Elbow38')
DEST = '/Game/Weapons/PKMLowpoly20260922/Animations'
ROOT = Path(r'D:\FPS3D\FPSGAME\Content\Weapons\PKMLowpoly20260922\Animations')
BACKUP = P / 'Before'
BACKUP.mkdir(exist_ok=True)
NAMES = ['A_PKM_idle', 'A_PKM_reload', 'A_PKM_reload_empty']
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
mesh = u.load_asset('/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
report = {}
try:
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    for name in NAMES:
        current = ROOT / (name + '.uasset')
        backup = BACKUP / (name + '.uasset')
        if current.exists() and not backup.exists():
            shutil.copy2(current, backup)
        ui = u.FbxImportUI()
        ui.automated_import_should_detect_type = False
        ui.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        ui.import_mesh = False
        ui.import_animations = True
        ui.import_materials = False
        ui.import_textures = False
        ui.skeleton = mesh.skeleton
        ui.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        ui.anim_sequence_import_data.set_editor_property('custom_sample_rate', 60 if name == 'A_PKM_idle' else 120)
        task = u.AssetImportTask()
        task.filename = str(P / 'Exports' / (name + '.fbx'))
        task.destination_path = DEST
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.options = ui
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sequence = u.load_asset(DEST + '/' + name)
        if not task.imported_object_paths or not sequence:
            raise RuntimeError('Import failed ' + name)
        if compression:
            sequence.set_editor_property('bone_compression_settings', compression)
        if not u.EditorAssetLibrary.save_loaded_asset(sequence):
            raise RuntimeError('Save failed ' + name)
        report[name] = {'seconds': sequence.get_play_length(), 'saved': True}
    (P / 'import_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    u.log('PKM_ELBOW38_IMPORT_COMPLETE')
finally:
    u.SystemLibrary.execute_console_command(None, f'{flag} {previous}')
