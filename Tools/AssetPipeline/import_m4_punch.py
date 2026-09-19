from pathlib import Path
import shutil
import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'SourceAssets/FirearmAudio20260913/M4Punch20260914'
backup = source / 'PreviousAssets'
backup.mkdir(exist_ok=True)
files = sorted(source.glob('S_M4_Original_*.wav'))
if len(files) != 4:
    raise RuntimeError('Expected four authored M4 WAV files')
for path in files:
    old = root / 'Content/Weapons/M4OriginalAudio20260913' / (path.stem + '.uasset')
    if old.exists() and not (backup / old.name).exists():
        shutil.copy2(old, backup / old.name)
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = '/Game/Weapons/M4OriginalAudio20260913'
    task.destination_name = path.stem
    task.automated = True
    task.replace_existing = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: ' + path.name)
unreal.log('M4_PUNCH_IMPORTED count=4')
