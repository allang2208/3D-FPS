"""Import the authored 715 shot and seven speedloader phases (no gameplay run)."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir()) / 'SourceAssets/DanWesson715RecordedAudio20260914'
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
receipt = []
for entry in [manifest['fire'], *manifest['clips']]:
    name = entry['asset']
    task = unreal.AssetImportTask()
    task.filename = str(root / 'Waves' / (name + '.wav'))
    task.destination_path = manifest['asset_root']
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Audio import failed: ' + name)
    sound = unreal.load_asset(task.imported_object_paths[0])
    sound.set_editor_property('loading_behavior', unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
    sound.set_editor_property('looping', False)
    unreal.EditorAssetLibrary.save_loaded_asset(sound)
    receipt.append({'asset': task.imported_object_paths[0], 'source': task.filename})
    unreal.log('DW715_RECORDED_AUDIO_IMPORTED ' + task.imported_object_paths[0])
(root / 'import-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
unreal.log('DW715_RECORDED_AUDIO_COMPLETE count=' + str(len(receipt)))
