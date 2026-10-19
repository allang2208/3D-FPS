"""Import and save the shared humanoid zombie palette; no playback.

The C++ side binds these assets through ConstructorHelpers on ANurseZombie, so
the script only needs to import + save SoundWaves under a stable path.
"""
from pathlib import Path
import json
import traceback
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/SharedHumanoidAudio20261016')
DEST = '/Game/Monsters/Shared/HumanoidAudioV1'
REV = 'HumanoidAudioV1'
lib = u.EditorAssetLibrary
report = dict(revision=REV, saved_sounds={}, complete=False, listened=False, runtime_tested=False)

def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

def save(asset):
    lib.set_metadata_tag(asset, 'Shared.HumanoidAudioRevision', REV)
    if not lib.save_loaded_asset(asset, False): raise RuntimeError('Could not save ' + asset.get_path_name())

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before importing shared humanoid audio')
        dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if any(p.startswith(DEST + '/') for p in dirty):
            raise RuntimeError('Preserve unsaved shared humanoid audio edits')
    manifest = json.loads((ROOT/'audio_manifest.json').read_text(encoding='utf-8'))
    lib.make_directory(DEST)
    for role, clip in manifest['clips'].items():
        name = Path(clip['file']).stem; path = DEST + '/' + name
        old = u.load_asset(path) if lib.does_asset_exist(path) else None
        if old and lib.get_metadata_tag(old, 'Shared.HumanoidAudioRevision') != REV:
            raise RuntimeError('Preserve existing unowned sound ' + path)
        if old:
            if not lib.delete_asset(path): raise RuntimeError('Could not delete prior ' + path)
        task = u.AssetImportTask()
        task.filename = str(ROOT/'Audio'/clip['file']); task.destination_path = DEST; task.destination_name = name
        task.automated = True; task.replace_existing = True; task.save = False; task.factory = u.SoundFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sound = u.load_asset(path)
        if not isinstance(sound, u.SoundWave): raise RuntimeError('SoundWave import failed ' + path)
        sound.set_editor_property('volume', 1.); sound.set_editor_property('pitch', 1.)
        sound.set_editor_property('looping', bool(clip.get('looping')))
        sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
        lib.set_metadata_tag(sound, 'Shared.HumanoidAudioRole', role)
        lib.set_metadata_tag(sound, 'Shared.HumanoidAudioSource',
            'OpenGameArt CC0 packs (StarNinjas 16 Monster Growls; Ogrebane Monster SFX); HumanoidAudioV1/audio_manifest.json')
        save(sound)
        report['saved_sounds'][role] = sound.get_path_name(); receipt()
    report['complete'] = True
    print(f'HUMANOID_AUDIO_V1_SAVED: {len(report["saved_sounds"])} SoundWaves at {DEST}; no playback.', flush=True)
except Exception:
    report['error'] = traceback.format_exc()
    raise
finally:
    receipt()
