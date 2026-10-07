"""Import S_M09_Resonance_V09.wav; the C++ Resonance FObjectFinder points here.
V07 stays on disk as the recovery asset."""
import unreal as u, json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/ResonanceV09')
DEST='/Game/Monsters/HangingBellM09/V09/Audio'
A=u.EditorAssetLibrary;T=u.AssetToolsHelpers.get_asset_tools()
report={'saved':[],'complete':False,'tested':False}
if not globals().get('M09_COMMANDLET',False):
 if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; preserve current game session')
wav=ROOT/'Audio/S_M09_Resonance_V09.wav';path=DEST+'/S_M09_Resonance_V09'
if A.does_asset_exist(path):
 snd=u.load_asset(path)
 if A.get_metadata_tag(snd,'M09Production')!='ResonanceV09':raise RuntimeError('Preserve existing asset '+path)
else:
 task=u.AssetImportTask();task.filename=str(wav);task.destination_path=DEST;task.destination_name='S_M09_Resonance_V09'
 task.automated=True;task.save=False;task.replace_existing=False;task.factory=u.SoundFactory()
 T.import_asset_tasks([task])
 snd=u.load_asset(path)
 if not snd:raise RuntimeError('Import failed '+str(wav))
snd.set_editor_property('volume',1.0)
A.set_metadata_tag(snd,'M09Production','ResonanceV09')
if not A.save_loaded_asset(snd,False):raise RuntimeError('Save failed '+path)
report['saved'].append(path);report['complete']=True
(ROOT/'Records').mkdir(exist_ok=True)
(ROOT/'Records/import_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M09_V09_RESONANCE_SAVED '+path)
