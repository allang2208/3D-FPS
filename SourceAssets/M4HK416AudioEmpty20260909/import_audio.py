import unreal,json,hashlib,wave
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416AudioEmpty20260909')
DEST='/Game/Weapons/M4HK416Audio'
report={}
for source,name in [('fire.wav','S_HK416_Fire'),('mag_out.wav','S_HK416_MagOut'),('mag_insert.wav','S_HK416_MagInsert'),('mag_seat.wav','S_HK416_MagSeat'),('bolt_release.wav','S_HK416_BoltRelease')]:
    p=OUT/'Audio'/source
    t=unreal.AssetImportTask();t.filename=str(p);t.destination_path=DEST;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);assert t.imported_object_paths
    sound=unreal.load_asset(DEST+'/'+name);assert isinstance(sound,unreal.SoundWave)
    sound.set_editor_property('loading_behavior',unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
    unreal.EditorAssetLibrary.save_loaded_asset(sound,only_if_is_dirty=False)
    with wave.open(str(p)) as w:duration=w.getnframes()/w.getframerate()
    report[name]={'asset':sound.get_path_name(),'duration':duration,'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(OUT/'audio_import.json').write_text(json.dumps(report,indent=2))
unreal.log('M4_HK416_AUDIO_IMPORT_PASS')
