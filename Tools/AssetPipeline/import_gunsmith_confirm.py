from pathlib import Path
import unreal
root = Path(unreal.Paths.project_dir())
task = unreal.AssetImportTask()
task.filename = str(root / 'SourceAssets/UIConfirm20260914/S_Gunsmith_Confirm.wav')
task.destination_path = '/Game/Audio/UIConfirm20260914'
task.destination_name = 'S_Gunsmith_Confirm'
task.automated = True
task.replace_existing = True
task.save = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Gunsmith confirm import failed')
unreal.log('GUNSMITH_CONFIRM_IMPORTED')
