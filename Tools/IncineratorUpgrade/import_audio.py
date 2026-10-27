"""Import only the new incinerator sound into an isolated content host."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/IncineratorUpgrade20261027'
if Path(u.Paths.project_dir()).resolve()!=(OUT/'AssetHost').resolve():
    raise RuntimeError('This script requires the isolated incinerator AssetHost')
DEST='/Game/Building/Incinerator20261027'
task=u.AssetImportTask()
for key,value in dict(filename=str(OUT/'S_IncineratorCombustionLoop.wav'),destination_path=DEST,
    destination_name='S_IncineratorCombustionLoop',automated=True,replace_existing=False,save=True).items():
    task.set_editor_property(key,value)
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
sound=u.EditorAssetLibrary.load_asset(DEST+'/S_IncineratorCombustionLoop')
if not isinstance(sound,u.SoundWave):raise RuntimeError('Sound import failed')
sound.set_editor_property('looping',True)
sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
if not u.EditorAssetLibrary.save_loaded_asset(sound,False):raise RuntimeError('Sound save failed')
(OUT/'audio-import.json').write_text(json.dumps({'saved':sound.get_path_name(),
    'duration':sound.get_editor_property('duration'),'looping':True,'auditioned':False},indent=2),encoding='utf-8')
print('INCINERATOR_SOUND_SAVED '+sound.get_path_name())
