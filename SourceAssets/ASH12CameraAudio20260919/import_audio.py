"""Import the user's ASH-12 shot; leave the shared rifle sound banks intact."""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
task = u.AssetImportTask()
task.filename = str(HERE / 'S_ASH12_Fire.wav')
task.destination_path = '/Game/Weapons/ASH12/Audio20260919'
task.destination_name = 'S_ASH12_Fire'
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('ASH-12 shot import failed')
sound = u.load_asset(task.imported_object_paths[0])
sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
sound.set_editor_property('looping', False)
if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
    raise RuntimeError('ASH-12 shot save failed')
receipt = {'source': task.filename, 'asset': sound.get_path_name(),
           'duration_seconds': sound.get_editor_property('duration')}
(HERE / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('ASH12_FIRE_IMPORT_COMPLETE ' + json.dumps(receipt))
