"""One gated authoring batch; preserve unrelated dirty packages and project identity."""
import json,runpy,traceback
from pathlib import Path
import unreal as u
HERE=Path(__file__).parent
if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('PIE running; no assets changed')
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
 plan=json.loads((HERE/'slot_plan.json').read_text())
 targets={v['path'] for v in plan.values()}|{'/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials'}
 if targets&dirty:raise RuntimeError('ASH12 targets have unsaved edits: '+str(sorted(targets&dirty)))
stages=[]
try:
 # The legacy stage clears instance overrides and rebuilds inherited presets.
 # Resume the latest finish once it has a receipt, including partial saves.
 scripts=('Refine02/apply_finish.py',) if (HERE/'Refine02/apply_receipt.json').exists() else ('build_region_master.py','install_uv.py','install_surface.py')
 for script in scripts:
  print('ASH12_WS_STAGE',script,flush=True)
  runpy.run_path(str(HERE/script),run_name='__main__');stages.append(script)
 (HERE/'batch_receipt.json').write_text(json.dumps({'completed':stages,'complete':True,'tested':False},indent=1))
except Exception:
 (HERE/'batch_receipt.json').write_text(json.dumps({'completed':stages,'complete':False,'error':traceback.format_exc(),'tested':False},indent=1))
 raise
