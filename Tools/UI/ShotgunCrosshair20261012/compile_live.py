"""Compile the existing HUD paint function in the already-running editor."""
import json
from pathlib import Path
from datetime import datetime
import unreal as u

out=Path(__file__).resolve().parent
log=Path(u.Paths.project_log_dir())/'FPSGAME.log'
offset=log.stat().st_size if log.exists() else 0
receipt={'started':datetime.now().isoformat(),'command':'LiveCoding.CompileSync','runtime_tested':False,'result':'pending'}
(out/'compile_request.json').write_text(json.dumps(receipt,indent=2))
u.log('SHOTGUN_RING_COMPILE_BEGIN')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
u.SystemLibrary.execute_console_command(editor.get_game_world() or editor.get_editor_world(),'LiveCoding.CompileSync')
u.log('SHOTGUN_RING_COMPILE_RETURN')
receipt.update(returned=datetime.now().isoformat(),result='command returned; see compiler output')
(out/'compile_request.json').write_text(json.dumps(receipt,indent=2))
if log.exists():
 with log.open('rb') as f:f.seek(offset);text=f.read().decode('utf-8',errors='replace')
 (out/'editor_compile.log').write_text(text,encoding='utf-8')
print('SHOTGUN_RING_COMPILE_RETURNED')
