from pathlib import Path
import unreal as u,json
ROOT=Path(__file__).resolve().parents[1];DEST='/Game/Building/PotionWorkbench20261015/RuntimeV2/Audio'
if Path(u.Paths.project_dir()).resolve()!=(ROOT.parent/'IntegrationV1/UEImportHost').resolve():raise RuntimeError('Wrong import host')
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;result=[]
for source in sorted((ROOT/'Authored/Audio').glob('*.wav')):
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name='SW_Alchemy'+source.stem
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    sound=next((o for o in task.get_objects() if isinstance(o,u.SoundWave)),None)
    if sound is None:raise RuntimeError('Audio import failed '+source.name)
    sound.set_editor_property('looping',source.stem in ('Grind','Boil'))
    E.set_metadata_tag(sound,'PotionWorkbench.Owner','PotionWorkbench20261015_RuntimeV2')
    if not E.save_loaded_asset(sound,False):raise RuntimeError('Audio save failed')
    result.append(sound.get_path_name())
(ROOT/'Receipts/import-audio.json').write_text(json.dumps({'saved':result,'auditioned':False},indent=2),'utf8')
u.log('ALCHEMY_AUDIO_SAVED')
