from pathlib import Path
from datetime import datetime
import unreal as u,json
O=Path(__file__).resolve().parent
log=Path(u.Paths.project_log_dir())/'FPSGAME.log';offset=log.stat().st_size if log.exists() else 0
r={'started':datetime.now().isoformat(),'command':'LiveCoding.CompileSync','runtime_tested':False,'base_dll_updated':False,'status':'requested'}
(O/'compile_receipt.json').write_text(json.dumps(r,indent=2))
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
u.SystemLibrary.execute_console_command(ed.get_game_world() or ed.get_editor_world(),'LiveCoding.CompileSync')
r.update(returned=datetime.now().isoformat(),status='command returned; see compiler log')
(O/'compile_receipt.json').write_text(json.dumps(r,indent=2))
if log.exists():
    with log.open('rb') as f:f.seek(offset);s=f.read().decode('utf-8',errors='replace')
    (O/'editor_compile.log').write_text(s,encoding='utf-8')
print('M24_RAIL_COMPILE_RETURNED')
