"""Save the user-selected BrightV2 clip as the shared pistol suppressor SoundWave."""
from pathlib import Path
import hashlib
import json
import unreal as u

ROOT = Path(__file__).resolve().parent
recipe = json.loads((ROOT / 'suppressed_provenance.json').read_text(encoding='utf8'))
TARGET = recipe['runtime_asset']
if TARGET in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve the unsaved shared pistol suppressor package.')
source = ROOT / recipe['output']
if hashlib.sha256(source.read_bytes()).hexdigest() != recipe['output_sha256']:
    raise RuntimeError('Shared suppressor source changed after selection.')
settings_source = u.load_asset(TARGET) or u.load_asset('/Game/Weapons/PitViper2011/Integrated20261002/Audio/S_PitViper2011_Fire')
if not settings_source:
    raise RuntimeError('Missing pistol SoundWave settings source.')
settings = {key: settings_source.get_editor_property(key) for key in ('volume', 'pitch', 'sound_class_object')}
task = u.AssetImportTask()
task.filename = str(source)
task.destination_path, task.destination_name = TARGET.rsplit('/', 1)
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
sound = u.load_asset(TARGET)
if not task.imported_object_paths or not isinstance(sound, u.SoundWave):
    raise RuntimeError('Shared pistol suppressor import failed.')
for key, value in settings.items():
    sound.set_editor_property(key, value)
sound.set_editor_property('looping', False)
sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
u.EditorAssetLibrary.set_metadata_tag(sound, 'PistolSuppressedRevision', recipe['revision'])
u.EditorAssetLibrary.set_metadata_tag(sound, 'PistolSuppressedRecipe', str(ROOT / 'suppressed_provenance.json'))
u.EditorAssetLibrary.set_metadata_tag(sound, 'AudioSourceAttribution', 'User-selected processed vpier.mp3 BrightV2; original user source rights retained.')
if not u.EditorLoadingAndSavingUtils.save_packages([sound.get_outermost()], False):
    raise RuntimeError('Shared pistol suppressor save failed.')
receipt = {
    'status': 'imported_and_saved', 'revision': recipe['revision'], 'asset': sound.get_path_name(),
    'source': str(source), 'source_sha256': recipe['output_sha256'], 'saved': True,
    'duration_seconds': recipe['duration_seconds'], 'sample_rate': recipe['sample_rate'], 'channels': recipe['channels'],
    'volume': settings['volume'], 'pitch': settings['pitch'],
    'sound_class': settings['sound_class_object'].get_path_name() if settings['sound_class_object'] else None,
    'compression': 'PCM', 'loading': 'ForceInline', 'supported_weapons': recipe['supported_weapons'],
    'native_source_connected': True, 'native_build_receipt': str(ROOT / 'build_receipt.json'),
    'auditioned': False, 'game_tested': False,
}
(ROOT / 'suppressed_import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
print('PISTOL_SHARED_SUPPRESSED_IMPORTED_SAVED', sound.get_path_name(), flush=True)
