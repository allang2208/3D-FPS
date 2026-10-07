"""Import authored M27 sounds and bind only audio/name defaults; no playback."""
from pathlib import Path
import json
import traceback
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/AudioV1')
DEST = '/Game/Monsters/MantisM27/AudioV1'
BP = '/Game/Monsters/MantisM27/BP_MantisM27'
REV = 'AudioV1'
lib = u.EditorAssetLibrary
manifest = json.loads((ROOT / 'audio_manifest.json').read_text(encoding='utf-8'))
report = dict(revision=REV, display_name='螳螂 M27', blueprint=BP,
              saved_sounds={}, blueprint_saved=False, complete=False,
              listened=False, runtime_tested=False)

def receipt():
    (ROOT / 'asset_receipt.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before importing M27 sound assets')
        dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if BP in dirty or any(p.startswith(DEST + '/') for p in dirty):
            raise RuntimeError('Preserve unsaved M27 Blueprint/audio changes')
    bp = u.load_asset(BP)
    if bp is None:
        raise RuntimeError('Missing M27 Blueprint: ' + BP)
    defaults = u.get_default_object(bp.generated_class())
    # Resolve the new native field before touching assets; requires the full build.
    defaults.get_editor_property('mantis_sounds')
    report['previous_display_name'] = str(defaults.get_editor_property('monster_display_name'))
    report['preserved_clips'] = {}
    for prop in ['left_slash_clip', 'right_slash_clip', 'pounce_windup_clip', 'pounce_flight_clip', 'pounce_land_clip']:
        clip = defaults.get_editor_property(prop)
        report['preserved_clips'][prop] = clip.get_path_name() if clip else None
    lib.make_directory(DEST)
    sounds = {}
    for role, clip in manifest['clips'].items():
        name = Path(clip['file']).stem
        path = DEST + '/' + name
        old = u.load_asset(path) if lib.does_asset_exist(path) else None
        if old and lib.get_metadata_tag(old, 'M27ProductionAudio') != REV:
            raise RuntimeError('Preserve unowned sound asset: ' + path)
        task = u.AssetImportTask()
        task.filename = str(ROOT / 'Audio' / clip['file'])
        task.destination_path = DEST
        task.destination_name = name
        task.automated = True
        task.save = False
        task.replace_existing = old is not None
        task.factory = u.SoundFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sound = u.load_asset(path)
        if not isinstance(sound, u.SoundWave):
            raise RuntimeError('SoundWave import failed: ' + path)
        sound.set_editor_property('looping', clip['looping'])
        sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
        lib.set_metadata_tag(sound, 'M27ProductionAudio', REV)
        lib.set_metadata_tag(sound, 'M27.AudioRole', role)
        lib.set_metadata_tag(sound, 'M27.AudioSource', 'Original synthesis + existing CC0 MP3 previews; SourceAssets/MantisM27/AudioV1/audio_manifest.json')
        if not lib.save_loaded_asset(sound, False):
            raise RuntimeError('Could not save sound: ' + path)
        sounds[u.Name(role)] = sound
        report['saved_sounds'][role] = sound.get_path_name()
        receipt()
    defaults.set_editor_property('mantis_sounds', sounds)
    defaults.set_editor_property('monster_display_name', '螳螂 M27')
    lib.set_metadata_tag(bp, 'MonsterIdentity', '螳螂 M27 / MantisM27')
    lib.set_metadata_tag(bp, 'M27.AudioRevision', REV + ': membrane cloak, horizontal scythe cuts, actual-contact pounce landing')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not lib.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save the M27 Blueprint')
    report['blueprint_saved'] = True
    report['complete'] = True
    print('M27_AUDIO_V1_SAVED: 15 SoundWaves and Blueprint; no playback or gameplay test.', flush=True)
except Exception:
    report['error'] = traceback.format_exc()
    raise
finally:
    receipt()
