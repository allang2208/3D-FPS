"""Import the selected descending-rain recording and its bounded voice group."""
import json
import shutil
import runpy
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
DEST = '/Game/Skills/MagicArrowRain20261026'
WAVE = DEST + '/S_ArrowRainBurst'
CON = DEST + '/CON_ArrowRainDescent'
ATT = DEST + '/ATT_ArrowRainDescent'
E = u.EditorAssetLibrary
SOURCE_WAVE = '/Game/Weapons/DarkBow20260925/AudioVideoDirect20260926/S_BowVideoDirect_Release.S_BowVideoDirect_Release'


def configure(sound):
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if CON in dirty or ATT in dirty:
        raise RuntimeError('Preserve unsaved arrow-rain audio settings')
    concurrency = u.load_asset(CON) if E.does_asset_exist(CON) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        'CON_ArrowRainDescent', DEST, u.SoundConcurrency, u.SoundConcurrencyFactory())
    settings = concurrency.get_editor_property('concurrency')
    settings.set_editor_property('max_count', 12)
    settings.set_editor_property('limit_to_owner', False)
    settings.set_editor_property('resolution_rule', u.MaxConcurrentResolutionRule.STOP_FARTHEST_THEN_OLDEST)
    settings.set_editor_property('voice_steal_release_time', .03)
    concurrency.set_editor_property('concurrency', settings)
    attenuation = u.load_asset(ATT) if E.does_asset_exist(ATT) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        'ATT_ArrowRainDescent', DEST, u.SoundAttenuation, u.SoundAttenuationFactory())
    falloff = attenuation.get_editor_property('attenuation')
    falloff.set_editor_property('attenuate', True)
    falloff.set_editor_property('spatialize', True)
    falloff.set_editor_property('distance_algorithm', u.AttenuationDistanceModel.LINEAR)
    falloff.set_editor_property('attenuation_shape', u.AttenuationShape.SPHERE)
    falloff.set_editor_property('attenuation_shape_extents', u.Vector(1000., 0., 0.))
    falloff.set_editor_property('falloff_distance', 7000.)
    falloff.set_editor_property('enable_occlusion', False)
    attenuation.set_editor_property('attenuation', falloff)
    sound.set_editor_property('volume', 1.)
    sound.set_editor_property('pitch', 1.)
    sound.set_editor_property('looping', False)
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    sound.set_editor_property('override_concurrency', False)
    sound.set_editor_property('concurrency_set', {concurrency})
    sound.set_editor_property('attenuation_settings', attenuation)
    E.set_metadata_tag(sound, 'ArrowRainAudioSource', 'Normal bow release: '+SOURCE_WAVE+'; selected 2026-11-09')
    E.set_metadata_tag(sound, 'ArrowRainAudioRole', 'Five staggered descending release voices; original seed release and ground impact unchanged')
    if not E.save_loaded_asset(concurrency, False):
        raise RuntimeError('Cannot save arrow-rain voice group')
    if not E.save_loaded_asset(attenuation, False):
        raise RuntimeError('Cannot save arrow-rain descent attenuation')
    return concurrency


def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before importing arrow-rain audio')
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if WAVE in dirty or CON in dirty or ATT in dirty:
        raise RuntimeError('Preserve unsaved arrow-rain audio assets')
    source = u.load_asset(SOURCE_WAVE)
    if not isinstance(source, u.SoundWave):
        raise RuntimeError('Normal bow release SoundWave is missing')
    if SOURCE_WAVE.split('.')[0] in dirty:
        raise RuntimeError('Preserve unsaved normal bow recording; save it before reuse')
    # Export the actual ordinary-shot asset, preserving its original waveform.
    source_file = OUT / 'Recordings/NormalBowRelease.wav'
    export = u.AssetExportTask()
    export.object = source
    export.filename = str(source_file)
    export.automated = True
    export.prompt = False
    export.replace_identical = True
    export.exporter = u.SoundExporterWAV()
    if not u.Exporter.run_asset_export_task(export):
        raise RuntimeError('Cannot export the normal bow recording')
    runpy.run_path(str(OUT / 'prepare.py'))['prepare'](source_file)
    for path in (WAVE, CON, ATT):
        disk = ROOT / ('Content/' + path.removeprefix('/Game/') + '.uasset')
        backup = OUT / 'Before' / disk.name
        if disk.exists() and not backup.exists():
            shutil.copy2(disk, backup)
    task = u.AssetImportTask()
    task.filename = str(OUT / 'S_ArrowRainBurst.wav')
    task.destination_path = DEST
    task.destination_name = 'S_ArrowRainBurst'
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.factory = u.SoundFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound = u.load_asset(WAVE)
    if not isinstance(sound, u.SoundWave) or not task.imported_object_paths:
        raise RuntimeError('Arrow-rain recording was not imported')
    concurrency = configure(sound)
    if not E.save_loaded_asset(sound, False):
        raise RuntimeError('Cannot save selected arrow-rain recording')
    receipt = dict(saved=True, assets=[sound.get_path_name(), concurrency.get_path_name(), ATT+'.ATT_ArrowRainDescent'],
                   source_asset=source.get_path_name(), playback_sequence_changed=False,
                   voices_per_cast=5, concurrent_voices=12, runtime_tested=False, auditioned=False)
    (OUT / 'saved-audio.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ARROW_RAIN_AUDIO_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    main()
