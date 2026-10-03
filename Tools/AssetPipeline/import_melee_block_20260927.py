from pathlib import Path
import unreal
root = Path(unreal.Paths.project_dir()) / 'SourceAssets/MeleeBlockAudio20260927'
for name in ('S_MeleeBlock_01', 'S_MeleeBlock_02'):
    task = unreal.AssetImportTask()
    task.filename = str(root / (name + '.wav'))
    task.destination_path = '/Game/Audio/MeleeBlock20260927'
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Audio import failed: ' + name)
    unreal.log('MELEE_BLOCK_IMPORTED ' + str(task.imported_object_paths))
