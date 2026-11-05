"""Import only the two M24 shot masters and publish their SoundWaves."""
from pathlib import Path
import hashlib,json
import unreal as ue

root=Path(__file__).resolve().parent
if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_content_dir())).resolve()!=(root.parents[1]/'Content').resolve():
    raise RuntimeError('Unexpected project')
recipe=json.loads((root/'mastering.json').read_text(encoding='utf-8'))
dest='/Game/Weapons/M24/FireAudio20261104'
library=ue.EditorAssetLibrary
targets=[dest+'/'+key for key in recipe['masters']]
dirty={p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(targets):raise RuntimeError('Unsaved M24 audio package retained')
if '-run=pythonscript' not in ue.SystemLibrary.get_command_line().lower():
    level=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('PIE active; preserve current session')
# Match the settings of the formerly used M24 normal sound for both shots.
donor=ue.load_asset('/Game/Weapons/SVDDragunov20260922/VideoAudio20260923/S_SVD_Fire_01')
if not isinstance(donor,ue.SoundWave):raise RuntimeError('Existing normal sound settings missing')
settings={k:donor.get_editor_property(k) for k in ('sound_class_object','volume','pitch')}
tasks=[]
for name,info in recipe['masters'].items():
    path=dest+'/'+name;src=root/info['wav']
    if hashlib.sha256(src.read_bytes()).hexdigest()!=info['sha256']:raise RuntimeError('Changed master '+name)
    existing=library.does_asset_exist(path)
    if existing and library.get_metadata_tag(ue.load_asset(path),'M24ShotMaster')!=str(src):
        raise RuntimeError('Occupied package '+path)
    t=ue.AssetImportTask();t.filename=str(src);t.destination_path=dest;t.destination_name=name
    t.automated=True;t.save=False;t.replace_existing=existing
    tasks.append(t)
ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
packages=[];saved=[]
for t in tasks:
    path=dest+'/'+str(t.destination_name)
    sound=ue.load_asset(path)
    if not t.imported_object_paths or not isinstance(sound,ue.SoundWave):raise RuntimeError('SoundWave import failed '+path)
    for prop,value in settings.items():sound.set_editor_property(prop,value)
    sound.set_editor_property('looping',False)
    sound.set_editor_property('loading_behavior',ue.SoundWaveLoadingBehavior.FORCE_INLINE)
    sound.set_sound_asset_compression_type(ue.SoundAssetCompressionType.PCM)
    library.set_metadata_tag(sound,'M24ShotMaster',str(t.filename))
    library.set_metadata_tag(sound,'RecordingSource','User-provided M24.mp3'+(' (suppressor sound design)' if str(t.destination_name).endswith('Suppressed') else ''))
    packages.append(sound.get_outermost());saved.append(sound.get_path_name())
if not ue.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Could not save M24 shot audio')
receipt={'saved':saved,'volume':settings['volume'],'pitch':settings['pitch'],
         'sound_class':settings['sound_class_object'].get_path_name() if settings['sound_class_object'] else None,
         'game_tested':False,'auditioned':False}
(root/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_FIRE_AUDIO_SAVED',saved,flush=True)
