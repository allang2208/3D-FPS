"""Build distance LODs from the fitted source; never retain a donor's old frame."""
import unreal as u
import json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KCommon20261017')
receipt=O/'Receipts/assets.json';R=json.loads(receipt.read_text())
targets=[r['path'] for r in R['parts'].values() if r['fit']]
headless='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless:
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
  if any(u.find_object(None,p) for p in targets):raise RuntimeError('Fitted part loaded during PIE; preserve it')
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
 if any(p.split('.')[0] in dirty for p in targets):raise RuntimeError('Unsaved fitted assets; preserve current edits')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved={}
for path in targets:
 mesh=u.load_asset(path)
 reduction=u.StaticMeshReductionOptions();reduction.auto_compute_lod_screen_size=False;rows=[]
 for ratio,screen in ((1.,1.),(.5,.18),(.25,.075)):
  row=u.StaticMeshReductionSettings();row.percent_triangles=ratio;row.screen_size=screen;rows.append(row)
 reduction.reduction_settings=rows
 sub.set_lods(mesh,reduction)
 if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
 saved[path]={'ratios':[1,.5,.25],'from':'Saiga fitted LOD0'}
 (O/'Receipts/lods.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
 print('SAIGA_FITTED_LODS_SAVED',path,flush=True)
