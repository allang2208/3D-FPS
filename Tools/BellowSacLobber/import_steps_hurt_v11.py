"""Append M-09 footsteps/hurt to the existing sound table, preserving V10."""
from pathlib import Path
import json
import traceback
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/StepsHurtV11')
DEST='/Game/Monsters/BellowSacLobber/V11/Audio'
BP='/Game/Monsters/BellowSacLobber/BP_BellowSacLobber'
REV='StepsHurtV11'; lib=u.EditorAssetLibrary
report=dict(revision=REV,saved_sounds={},saved_concurrency=[],blueprint_saved=False,
    complete=False,listened=False,runtime_tested=False)
def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    lib.set_metadata_tag(asset,'Bellow.StepsHurtRevision',REV)
    if not lib.save_loaded_asset(asset,False): raise RuntimeError('Cannot save '+asset.get_path_name())
try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before importing M-09 audio')
        dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if BP in dirty or any(p.startswith(DEST+'/') for p in dirty):
            raise RuntimeError('Preserve unsaved M-09 Blueprint/audio changes')
    bp=u.load_asset(BP)
    if not bp: raise RuntimeError('Missing M-09 Blueprint')
    defaults=u.get_default_object(bp.generated_class())
    sounds=dict(defaults.get_editor_property('bellow_sounds'))
    report['previous_roles']={str(k):v.get_path_name() if v else None for k,v in sounds.items()}
    report['preserved_creature_gain']=defaults.get_editor_property('creature_audio_gain')
    manifest=json.loads((ROOT/'audio_manifest.json').read_text(encoding='utf-8'))
    lib.make_directory(DEST)
    concurrency={}
    for group,count in [('Footstep',6),('Hurt',4)]:
        name='CON_Bellow'+group;path=DEST+'/'+name
        asset=u.load_asset(path) if lib.does_asset_exist(path) else None
        if asset and lib.get_metadata_tag(asset,'Bellow.StepsHurtRevision')!=REV:
            raise RuntimeError('Preserve unowned asset '+path)
        if not asset: asset=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.SoundConcurrency,u.SoundConcurrencyFactory())
        settings=asset.get_editor_property('concurrency')
        settings.set_editor_property('max_count',count);settings.set_editor_property('limit_to_owner',False)
        settings.set_editor_property('resolution_rule',u.MaxConcurrentResolutionRule.STOP_FARTHEST_THEN_OLDEST)
        settings.set_editor_property('voice_steal_release_time',.035)
        asset.set_editor_property('concurrency',settings);save(asset)
        concurrency[group]=asset;report['saved_concurrency'].append(asset.get_path_name());receipt()
    for role,clip in manifest['clips'].items():
        name=Path(clip['file']).stem;path=DEST+'/'+name
        old=u.load_asset(path) if lib.does_asset_exist(path) else None
        if old and lib.get_metadata_tag(old,'Bellow.StepsHurtRevision')!=REV:
            raise RuntimeError('Preserve unowned sound '+path)
        task=u.AssetImportTask();task.filename=str(ROOT/'Audio'/clip['file'])
        task.destination_path=DEST;task.destination_name=name;task.automated=True
        task.replace_existing=old is not None;task.save=False;task.factory=u.SoundFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sound=u.load_asset(path)
        if not isinstance(sound,u.SoundWave): raise RuntimeError('Failed SoundWave import '+path)
        sound.set_editor_property('volume',1.);sound.set_editor_property('pitch',1.)
        sound.set_editor_property('looping',False)
        sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
        sound.set_editor_property('override_concurrency',False)
        group='Footstep' if role.startswith('Footstep') else 'Hurt'
        sound.set_editor_property('concurrency_set',{concurrency[group]})
        lib.set_metadata_tag(sound,'Bellow.AudioRole',role)
        lib.set_metadata_tag(sound,'Bellow.AudioSource','Retained CC0 V10 HQ MP3 ingredients + original synthesis; StepsHurtV11/audio_manifest.json')
        save(sound);sounds[u.Name(role)]=sound
        report['saved_sounds'][role]=sound.get_path_name();receipt()
    defaults.set_editor_property('bellow_sounds',sounds)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report['blueprint_saved']=True;report['blueprint']=bp.get_path_name()
    report['complete']=True
    print('BELLOW_STEPS_HURT_V11_SAVED: 7 SoundWaves, 2 concurrency assets, original Blueprint; V10 retained.',flush=True)
except Exception:
    report['error']=traceback.format_exc()
    raise
finally: receipt()
