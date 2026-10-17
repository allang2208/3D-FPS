"""Apply the M870 aim-gate fix in the already running editor; no gameplay test."""
import unreal as u,json
from pathlib import Path
from datetime import datetime
O=Path(__file__).parent
log=Path(u.Paths.project_log_dir())/'FPSGAME.log';offset=log.stat().st_size if log.exists() else 0
R={'started':datetime.now().isoformat(),'command':'LiveCoding.CompileSync','runtime_tested':False,'base_dll_updated':False,'status':'requested'}
(O/'compile_receipt.json').write_text(json.dumps(R,indent=2))
u.log('M870_ADS_COMPILE_BEGIN')
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
u.SystemLibrary.execute_console_command(ed.get_game_world() or ed.get_editor_world(),'LiveCoding.CompileSync')
u.log('M870_ADS_COMPILE_RETURN')
R.update(returned=datetime.now().isoformat(),status='command returned; compiler result recorded separately')
(O/'compile_receipt.json').write_text(json.dumps(R,indent=2))
if log.exists():
 with log.open('rb') as f:f.seek(offset);text=f.read().decode('utf-8',errors='replace')
 (O/'editor_compile.log').write_text(text,encoding='utf-8')
print('M870_ADS_COMPILE_RETURNED',flush=True)
