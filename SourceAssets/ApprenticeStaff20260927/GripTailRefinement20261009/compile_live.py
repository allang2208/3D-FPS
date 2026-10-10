"""Compile the existing native component function changes without starting play."""
import unreal as u,json
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:raise RuntimeError('PIE active; compilation deferred')
r={'started':datetime.now().isoformat(),'command':'LiveCoding.CompileSync','tested':False}
(P/'compile-request.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
u.log('STAFF_TAIL_DYNAMICS_COMPILE_BEGIN '+r['started'])
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'LiveCoding.CompileSync')
r['returned']=datetime.now().isoformat()
(P/'compile-request.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
u.log('STAFF_TAIL_DYNAMICS_COMPILE_RETURN '+r['returned'])
