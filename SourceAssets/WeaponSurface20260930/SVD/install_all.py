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
 targets={v['path'] for v in plan.values()}|{'/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials'}
 targets.update(p for p in dirty if p.startswith('/Game/Weapons/SVDDragunov20260922/SurfaceStandard20261001/'))
 if targets&dirty:raise RuntimeError('SVD targets have unsaved edits: '+str(sorted(targets&dirty)))
stages=[]
try:
 # Resume the latest saved production revision without resetting its material
 # parents, fine grain, source normals or part settings through older stages.
 if (HERE/'Refine04/apply_receipt.json').exists():
  scripts=('Refine04/apply_finish.py',)
 elif (HERE/'Refine03/apply_receipt.json').exists():
  scripts=('Refine03/apply_finish.py',)
 else:
  scripts=('build_adapters.py','install_uv.py','install_surface.py','MagazineSatin02/apply_finish.py')
 for script in scripts:
  print('SVD_WS_STAGE',script,flush=True)
  runpy.run_path(str(HERE/script),run_name='__main__');stages.append(script)
 (HERE/'batch_receipt.json').write_text(json.dumps({'completed':stages,'complete':True,'tested':False},indent=1))
except Exception:
 (HERE/'batch_receipt.json').write_text(json.dumps({'completed':stages,'complete':False,'error':traceback.format_exc(),'tested':False},indent=1))
 raise
