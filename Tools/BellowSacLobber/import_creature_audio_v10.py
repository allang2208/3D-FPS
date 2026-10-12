"""Import and save M-09 creature cues plus Blueprint references; no playback."""
from pathlib import Path
import json
import traceback
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/CreatureAudioV10')
DEST = '/Game/Monsters/BellowSacLobber/V10/Audio'
BP = '/Game/Monsters/BellowSacLobber/BP_BellowSacLobber'
REV = 'CreatureAudioV10'
lib = u.EditorAssetLibrary
report = dict(revision=REV, saved_sounds={}, saved_concurrency=[], blueprint_saved=False,
    complete=False, listened=False, runtime_tested=False)

def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def save(asset):
    lib.set_metadata_tag(asset,'Bellow.CreatureAudioRevision',REV)
    if not lib.save_loaded_asset(asset,False): raise RuntimeError('Could not save '+asset.get_path_name())

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before importing M-09 audio')
        dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if BP in dirty or any(p.startswith(DEST+'/') for p in dirty):
            raise RuntimeError('Preserve unsaved M-09 Blueprint/audio edits')
    bp=u.load_asset(BP)
    if not bp: raise RuntimeError('Missing M-09 Blueprint')
    defaults=u.get_default_object(bp.generated_class())
    defaults.get_editor_property('bellow_sounds')
    manifest=json.loads((ROOT/'audio_manifest.json').read_text(encoding='utf-8'))
    lib.make_directory(DEST)
    concurrency={}
    for role,count in [('Alert',4),('Attack',8),('Death',6)]:
        name='CON_Bellow'+role
        path=DEST+'/'+name
        asset=u.load_asset(path) if lib.does_asset_exist(path) else None
        if asset and lib.get_metadata_tag(asset,'Bellow.CreatureAudioRevision')!=REV:
            raise RuntimeError('Preserve existing unowned asset '+path)
        if not asset: asset=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.SoundConcurrency,u.SoundConcurrencyFactory())
        settings=asset.get_editor_property('concurrency')
        settings.set_editor_property('max_count',count)
        settings.set_editor_property('limit_to_owner',False)
        settings.set_editor_property('resolution_rule',u.MaxConcurrentResolutionRule.STOP_FARTHEST_THEN_OLDEST)
        settings.set_editor_property('voice_steal_release_time',.045)
        asset.set_editor_property('concurrency',settings)
        save(asset);concurrency[role]=asset
        report['saved_concurrency'].append(asset.get_path_name());receipt()
    # Later additive palettes (V11 footsteps/hurt) survive a V10 rebuild.
    # User removed the inhaling charge cue on 2026-10-12; rebuilding must keep it disabled.
    sounds={key:value for key,value in defaults.get_editor_property('bellow_sounds').items() if str(key)!='Charge'}
    for role,clip in manifest['clips'].items():
        if role=='Charge': continue
        name=Path(clip['file']).stem;path=DEST+'/'+name
        old=u.load_asset(path) if lib.does_asset_exist(path) else None
        if old and lib.get_metadata_tag(old,'Bellow.CreatureAudioRevision')!=REV:
            raise RuntimeError('Preserve existing unowned sound '+path)
        task=u.AssetImportTask()
        task.filename=str(ROOT/'Audio'/clip['file']);task.destination_path=DEST;task.destination_name=name
        task.automated=True;task.replace_existing=old is not None;task.save=False;task.factory=u.SoundFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sound=u.load_asset(path)
        if not isinstance(sound,u.SoundWave): raise RuntimeError('SoundWave import failed '+path)
        sound.set_editor_property('volume',1.);sound.set_editor_property('pitch',1.)
        sound.set_editor_property('looping',False)
        sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
        sound.set_editor_property('override_concurrency',False)
        group='Alert' if role.startswith('Alert') else 'Death' if role.startswith('Death') or role=='BodyFall' else 'Attack'
        sound.set_editor_property('concurrency_set',{concurrency[group]})
        lib.set_metadata_tag(sound,'Bellow.AudioRole',role)
        lib.set_metadata_tag(sound,'Bellow.AudioSource','CC0 HQ MP3 previews + original synthesis; CreatureAudioV10/audio_manifest.json')
        save(sound);sounds[u.Name(role)]=sound
        report['saved_sounds'][role]=sound.get_path_name();receipt()
    defaults.set_editor_property('bellow_sounds',sounds)
    defaults.set_editor_property('creature_audio_gain',1.35)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    report['blueprint_saved']=True
    report['blueprint']=bp.get_path_name()
    report['gain']=1.35
    report['complete']=True
    print(f'BELLOW_CREATURE_AUDIO_V10_SAVED: {len(report["saved_sounds"])} SoundWaves, 3 concurrency assets and Blueprint; Charge disabled; no playback.',flush=True)
except Exception:
    report['error']=traceback.format_exc()
    raise
finally:
    receipt()
