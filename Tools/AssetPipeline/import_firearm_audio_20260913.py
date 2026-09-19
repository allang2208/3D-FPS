from pathlib import Path
import unreal

source = Path(unreal.Paths.project_dir()) / 'SourceAssets/FirearmAudio20260913/Wav'
destination = '/Game/Weapons/FreeFirearmAudio20260913'
tasks = []
for path in sorted(source.glob('*.wav')):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = destination
    task.destination_name = path.stem
    task.automated = True
    task.replace_existing = True
    task.save = True
    tasks.append(task)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for task in tasks:
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: ' + task.filename)
unreal.log('FREE_FIREARM_AUDIO_IMPORTED count=' + str(len(tasks)))
