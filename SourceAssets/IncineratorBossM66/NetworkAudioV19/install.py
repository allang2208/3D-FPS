from pathlib import Path
import json,unreal as u
root=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/NetworkAudioV19')
exec(compile((root/'author_smoke.py').read_text(encoding='utf8'),'author_smoke.py','exec'))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();DEST='/Game/Monsters/IncineratorBossM66/NetworkAudioV19'
bp=u.load_asset('/Game/Monsters/IncineratorBossM66/BP_M66RigPreview');cdo=u.get_default_object(bp.generated_class())
att=A.duplicate_asset('ATT_M66Body',DEST,u.load_asset('/Game/Monsters/IncineratorBossM66/FurnaceBreathV17/ATT_M66Furnace')) if not E.does_asset_exist(DEST+'/ATT_M66Body') else u.load_asset(DEST+'/ATT_M66Body')
settings=att.get_editor_property('attenuation');settings.set_editor_property('attenuation_shape_extents',u.Vector(220,0,0));settings.set_editor_property('falloff_distance',2300.);att.set_editor_property('attenuation',settings)
if not E.save_loaded_asset(att,False):raise RuntimeError('M66 audio attenuation save failed')
manifest=json.loads((root/'audio_manifest.json').read_text(encoding='utf8'));sounds={};saved=[]
for role,row in manifest['clips'].items():
    task=u.AssetImportTask();task.filename=row['file'];task.destination_path=DEST;task.destination_name='S_M66_'+role+'_V19';task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);sound=u.load_asset(DEST+'/'+task.destination_name)
    if not sound:raise RuntimeError('Missing imported '+role)
    sound.set_editor_property('looping',row['loop']);sound.set_editor_property('volume',1.);sound.set_editor_property('pitch',1.);sound.set_editor_property('attenuation_settings',att)
    sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
    E.set_metadata_tag(sound,'M66.V19.Source',row['source']);E.set_metadata_tag(sound,'M66.V19.Role',role)
    if not E.save_loaded_asset(sound,False):raise RuntimeError('M66 audio save failed '+role)
    sounds[u.Name(role)]=sound;saved.append(sound.get_path_name())
cdo.set_editor_property('body_sounds',sounds);cdo.set_editor_property('body_audio_attenuation',att);cdo.set_editor_property('body_audio_gain',.8)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 blueprint save failed')
report={'complete':True,'sounds':saved,'blueprint':bp.get_path_name(),'sound_slots':len(sounds),'smoke':DEST+'/NS_M66HistorySoot','auditioned':False}
(root/'install_receipt.json').write_text(json.dumps(report,indent=2));print('M66_V19_INSTALLED '+json.dumps(report))
