"""Create AKM-only assets in the current editor. No PIE or playback."""
from pathlib import Path
import json
import unreal as u

HERE = Path(__file__).resolve().parent
DEST = '/Game/Weapons/AKM/SuppressedAudio20260921'
receipt = []
for cue in ('Suppressed',):
    name = 'S_AKM_' + cue
    original = u.load_asset('/Game/Weapons/AKM/VideoAudio20260921/S_AKM_Fire')
    if original is None:
        raise RuntimeError('Missing original audio settings: ' + name)
    task = u.AssetImportTask()
    task.filename = str(HERE / (name + '.wav'))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: ' + name)
    sound = u.load_asset(task.imported_object_paths[0])
    for prop in ('volume', 'pitch', 'sound_class_object', 'compression_quality'):
        sound.set_editor_property(prop, original.get_editor_property(prop))
    sound.set_editor_property('looping', False)
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
        raise RuntimeError('Save failed: ' + name)
    receipt.append(dict(asset=sound.get_path_name(), source=task.filename))
    (HERE / 'import-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('AKM_SUPPRESSED_AUDIO_IMPORTED ' + json.dumps(receipt))
