"""Import and save the Dealer demon laugh only; no playback, world load or tests."""
from pathlib import Path
import json
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
TARGET = '/Game/Weapons/Dealer20261004/Audio/S_Dealer_DemonLaugh'
recipe = json.loads((ROOT / 'provenance.json').read_text(encoding='utf-8'))
receipt = {'complete': False, 'saved_assets': [], 'source_page': recipe['source_page'],
           'source_sha256': recipe['source_sha256'], 'license': recipe['license'],
           'listened': False, 'gameplay_tested': False}


def record():
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


record()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve() != (PROJECT / 'Content').resolve():
    raise RuntimeError('Wrong content mount; no audio changed.')
if TARGET in {package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve the unsaved Dealer laugh asset.')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Preserve the active game session; import after it ends.')
task = u.AssetImportTask()
task.filename = str(ROOT / recipe['output'])
task.destination_path, task.destination_name = TARGET.rsplit('/', 1)
task.automated = True
task.replace_existing = True
task.save = False
task.factory = u.SoundFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
sound = u.load_asset(TARGET, u.SoundWave)
if not sound or not task.imported_object_paths:
    raise RuntimeError('Dealer laugh import did not produce a SoundWave.')
sound.set_editor_property('looping', False)
sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
for key, value in {'DealerLaughSource': recipe['source_page'], 'DealerLaughAuthor': recipe['author'],
                   'DealerLaughLicense': recipe['license'], 'DealerLaughMasterSHA256': recipe['output_sha256']}.items():
    u.EditorAssetLibrary.set_metadata_tag(sound, key, value)
if not u.EditorAssetLibrary.save_loaded_asset(sound, only_if_is_dirty=False):
    raise RuntimeError('Dealer laugh asset could not be saved.')
receipt['saved_assets'].append(TARGET)
receipt['complete'] = True
record()
print('DEALER_DEMON_LAUGH_SAVED CC0 played=false tested=false')
