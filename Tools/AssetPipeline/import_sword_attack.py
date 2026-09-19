from pathlib import Path
import unreal
root = Path(unreal.Paths.project_dir())
task = unreal.AssetImportTask()
task.filename = str(root / 'SourceAssets/SwordAttack20260914/S_Sword_Attack.wav')
task.destination_path = '/Game/Audio/SwordAttack20260914'
task.destination_name = 'S_Sword_Attack'
task.automated = True
task.replace_existing = True
task.save = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Sword attack audio import failed')
unreal.log('SWORD_ATTACK_LAYER_IMPORTED')
