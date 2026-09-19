"""Import and save only the four ASH-specific suppressed one-shots in-editor."""
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
source_sound = u.load_asset('/Game/Weapons/ASH12/Audio20260919/S_ASH12_Fire')
if source_sound is None:
    raise RuntimeError('ASH normal fire SoundWave is required for matching playback settings.')
tasks = []
for index in range(1, 5):
    name = f'S_ASH12_Suppressed_{index:02d}'
    task = u.AssetImportTask()
    task.filename = str(HERE / (name + '.wav'))
    task.destination_path = '/Game/Weapons/ASH12/SuppressedAudio20260920'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    tasks.append(task)
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
receipt = []
for task in tasks:
    if not task.imported_object_paths:
        raise RuntimeError('ASH suppressed audio import failed: ' + task.filename)
    sound = u.load_asset(task.imported_object_paths[0])
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    sound.set_editor_property('looping', False)
    for name in ('volume', 'pitch', 'sound_class_object', 'compression_quality'):
        sound.set_editor_property(name, source_sound.get_editor_property(name))
    if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
        raise RuntimeError('ASH suppressed audio save failed: ' + sound.get_path_name())
    receipt.append({'source': task.filename, 'asset': sound.get_path_name(),
                    'volume': sound.get_editor_property('volume'),
                    'pitch': sound.get_editor_property('pitch')})
(HERE / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('ASH12_SUPPRESSED_IMPORT_COMPLETE ' + json.dumps(receipt))
