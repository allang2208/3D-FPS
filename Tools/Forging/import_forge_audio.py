"""Replace only the existing hammer-contact sound and save it; no runtime play."""
import datetime
import json
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir())
source = root / 'SourceAssets/ForgeInteraction20260927/ForgeHammerImpact.wav'
destination = '/Game/Props/ForgeInteraction20260927'
target = destination + '/SW_ForgeHammerImpact'
dirty = {str(package.get_path_name()) for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if target in dirty:
    raise RuntimeError('Unsaved hammer sound edits; preserving editor work: ' + target)

task = u.AssetImportTask()
task.filename = str(source)
task.destination_path = destination
task.destination_name = 'SW_ForgeHammerImpact'
task.automated = True
task.replace_existing = True
task.save = False
task.factory = u.SoundFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Hammer sound import produced no asset')
sound = u.load_asset(target)
if not isinstance(sound, u.SoundWave):
    raise RuntimeError('Hammer sound is not a SoundWave')
sound.set_editor_property('looping', False)
if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
    raise RuntimeError('Could not save hammer sound')

receipt = {'asset': sound.get_path_name(), 'source': str(source),
           'duration_seconds': sound.get_editor_property('duration'),
           'trigger': 'existing hammer contact', 'runtime_tested': False}
path = source.parent / ('audio-import-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('FORGE_AUDIO_SAVED ' + json.dumps(receipt, ensure_ascii=False), flush=True)
