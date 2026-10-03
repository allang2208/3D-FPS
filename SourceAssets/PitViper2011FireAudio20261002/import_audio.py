"""Replace and save the existing Pit Viper Fire SoundWave without playing it."""
from pathlib import Path
import hashlib
import json
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
TARGET = '/Game/Weapons/PitViper2011/Integrated20261002/Audio/S_PitViper2011_Fire'
recipe = json.loads((ROOT / 'provenance.json').read_text(encoding='utf8'))
source = ROOT / recipe['output']
if hashlib.sha256(source.read_bytes()).hexdigest() != recipe['output_sha256']:
    raise RuntimeError('Authored source changed after its provenance was saved.')
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve() != (PROJECT / 'Content').resolve():
    raise RuntimeError('Wrong project content mount; no audio changed.')
targets = {TARGET, '/Game/Weapons/PistolSharedAudio20261002/S_Pistol_Suppressed'}
if targets & {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve the unsaved Pit Viper Fire package.')
subsystem = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if subsystem and subsystem.get_game_world():
    raise RuntimeError('Preserve the active game session; import after it ends.')
old = u.load_asset(TARGET)
if not isinstance(old, u.SoundWave):
    raise RuntimeError('Expected the current production Fire SoundWave at ' + TARGET)
preserved = {name: old.get_editor_property(name) for name in ('volume', 'pitch', 'sound_class_object')}
previous = {
    'asset': old.get_path_name(), 'duration_seconds': old.get_editor_property('duration'),
    'volume': preserved['volume'], 'pitch': preserved['pitch'],
    'sound_class': preserved['sound_class_object'].get_path_name() if preserved['sound_class_object'] else None,
}
(ROOT / 'previous_audio_settings.json').write_text(json.dumps(previous, indent=2), encoding='utf8')
task = u.AssetImportTask()
task.filename = str(source)
task.destination_path, task.destination_name = TARGET.rsplit('/', 1)
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
sound = u.load_asset(TARGET)
if not task.imported_object_paths or not isinstance(sound, u.SoundWave):
    raise RuntimeError('Pit Viper firing import did not produce its SoundWave.')
for name, value in preserved.items():
    sound.set_editor_property(name, value)
sound.set_editor_property('looping', False)
sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
u.EditorAssetLibrary.set_metadata_tag(sound, 'PitViperFireSourceSHA256', recipe['source_sha256'])
u.EditorAssetLibrary.set_metadata_tag(sound, 'PitViperFireRecipe', str(ROOT / 'provenance.json'))
u.EditorAssetLibrary.set_metadata_tag(sound, 'PitViperFireRevision', recipe.get('revision', 'CleanV1'))
u.EditorAssetLibrary.set_metadata_tag(sound, 'AudioSourceAttribution', 'User-provided ' + Path(recipe['input_actual_path']).name + '; processed 20261002; original source rights retained.')
if not u.EditorLoadingAndSavingUtils.save_packages([sound.get_outermost()], False):
    raise RuntimeError('Pit Viper Fire package could not be saved.')
receipt = {
    'revision': recipe.get('revision', 'CleanV1'),
    'status': 'imported_and_saved', 'asset': sound.get_path_name(), 'source': str(source),
    'source_sha256': recipe['output_sha256'], 'saved': True,
    'duration_seconds': recipe['duration_seconds'], 'sample_rate': recipe['sample_rate'],
    'channels': recipe['channels'], 'volume': preserved['volume'], 'pitch': preserved['pitch'],
    'sound_class': previous['sound_class'], 'compression': 'PCM', 'loading': 'ForceInline',
    'existing_runtime_routes_preserved': ['single', 'dual', 'staff-offhand'],
    'native_code_changed': True, 'native_build_required': True,
    'native_build_receipt': str(ROOT / 'build_receipt.json'),
    'auditioned': False, 'game_tested': False,
}
(ROOT / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
script = ROOT / 'import_suppressed.py'
exec(compile(script.read_text(encoding='utf8'), str(script), 'exec'), {'__file__': str(script), '__name__': '__main__'})
script = ROOT / 'record_delivery.py'
exec(compile(script.read_text(encoding='utf8'), str(script), 'exec'), {'__file__': str(script), '__name__': '__main__'})
print('PIT_VIPER_FIRE_IMPORTED_SAVED', sound.get_path_name(), flush=True)
