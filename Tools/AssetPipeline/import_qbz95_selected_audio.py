from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir())/'SourceAssets/FirearmAudio20260913/QBZ95Selected'
for p in sorted(root.glob('*.wav')):
    task=unreal.AssetImportTask()
    task.filename=str(p)
    task.destination_path='/Game/Weapons/FreeFirearmAudio20260913'
    task.destination_name=p.stem.replace('Selected', 'Fire')
    task.automated=True
    task.replace_existing=True
    task.save=True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths: raise RuntimeError(str(p))
    sound=unreal.load_asset(task.imported_object_paths[0])
    sound.set_editor_property('loading_behavior',unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
    unreal.EditorAssetLibrary.save_loaded_asset(sound)
unreal.log('QBZ95_SELECTED_AUDIO_IMPORTED')
