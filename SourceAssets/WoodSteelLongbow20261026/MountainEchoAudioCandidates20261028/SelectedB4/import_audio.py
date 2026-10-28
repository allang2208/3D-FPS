"""Import/save the selected B4 impact with spatial attenuation and voice limits."""
import hashlib
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
SOURCE = HERE/'S_MountainEcho_EnergyImpact.wav'
DEST = '/Game/Weapons/WoodSteelLongbow20261026/MountainEchoAudioB4'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('Preserve running Play session; end Play before importing the sound')
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:
    raise RuntimeError('Preserve unsaved B4 audio assets: '+str(dirty))
EAL.make_directory(DEST)


def create(name, kind, factory):
    path = DEST+'/'+name
    return u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, DEST, kind, factory)


attenuation = create('ATT_MountainEchoImpact', u.SoundAttenuation, u.SoundAttenuationFactory())
settings = attenuation.get_editor_property('attenuation')
for key, value in {'attenuate': True, 'spatialize': True,
                   'attenuation_shape_extents': u.Vector(400, 0, 0),
                   'falloff_distance': 7000.}.items():
    settings.set_editor_property(key, value)
attenuation.set_editor_property('attenuation', settings)
concurrency = create('CON_MountainEchoImpact', u.SoundConcurrency, u.SoundConcurrencyFactory())
settings = concurrency.get_editor_property('concurrency')
settings.set_editor_property('max_count', 8)
settings.set_editor_property('limit_to_owner', False)
settings.set_editor_property('resolution_rule', u.MaxConcurrentResolutionRule.STOP_FARTHEST_THEN_OLDEST)
settings.set_editor_property('voice_steal_release_time', .03)
concurrency.set_editor_property('concurrency', settings)

task = u.AssetImportTask()
task.filename = str(SOURCE)
task.destination_path = DEST
task.destination_name = 'S_MountainEcho_EnergyImpact'
task.automated = True
task.replace_existing = True
task.save = False
task.factory = u.SoundFactory()
TOOLS.import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('B4 SoundWave import failed')
sound = u.load_asset(task.imported_object_paths[0])
if not isinstance(sound, u.SoundWave):
    raise RuntimeError('Expected imported SoundWave')
for key, value in {'volume': 1., 'pitch': 1., 'looping': False, 'compression_quality': 100,
                   'loading_behavior': u.SoundWaveLoadingBehavior.FORCE_INLINE,
                   'attenuation_settings': attenuation, 'override_concurrency': False,
                   'concurrency_set': {concurrency}}.items():
    sound.set_editor_property(key, value)
sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
EAL.set_metadata_tag(sound, 'MountainEchoAudioSelection', 'B4 Energy Fusion; selected for integration 2026-10-28')
EAL.set_metadata_tag(sound, 'AudioAttribution', 'TannerSound / Laser Magic Spell Impacts / CC BY 4.0; artisticdude swish / CC0; original energy synthesis. See ColdSteelData/Licenses/MountainEchoEnergyImpactB4.txt')
saved = []
for asset in [attenuation, concurrency, sound]:
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    saved.append(asset.get_path_name())
receipt = {'complete': True, 'selected_revision': 'B4 Energy Fusion', 'saved_assets': saved,
           'source_file': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
           'volume': 1., 'pitch': 1., 'looping': False, 'compression': 'PCM', 'loading': 'ForceInline',
           'spatialized': True, 'inner_radius_cm': 400, 'falloff_distance_cm': 7000,
           'maximum_concurrent_voices': 8, 'played': False, 'runtime_tested': False}
(HERE/'import-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('MOUNTAIN_ECHO_B4_AUDIO_SAVED '+json.dumps(receipt))
