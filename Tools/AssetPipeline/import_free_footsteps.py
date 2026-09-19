from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir())/'SourceAssets/FreeFootsteps20260913/Wav'
for p in sorted(root.glob('*.wav')):
    t=unreal.AssetImportTask()
    t.filename=str(p);t.destination_path='/Game/Audio/FreeFootsteps';t.destination_name=p.stem
    t.automated=True;t.replace_existing=True;t.save=True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    if not t.imported_object_paths:raise RuntimeError(str(p))
    sound=unreal.load_asset(t.imported_object_paths[0])
    sound.set_editor_property('loading_behavior',unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
    unreal.EditorAssetLibrary.save_loaded_asset(sound)
unreal.log('FREE_FOOTSTEPS_IMPORTED')
