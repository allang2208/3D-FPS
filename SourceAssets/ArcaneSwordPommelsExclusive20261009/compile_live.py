"""Apply existing-function changes through the already-running editor."""
from pathlib import Path
from datetime import datetime
import json
import unreal as u
P=Path(__file__).resolve().parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
request={'started':datetime.now().isoformat(),'command':'LiveCoding.CompileSync','result':'pending','tested':False}
(P/'compile-request.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
u.log('ARCANE_POMMELS_COMPILE_BEGIN '+request['started'])
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'LiveCoding.CompileSync')
request.update(returned=datetime.now().isoformat(),result='command returned; compiler result is recorded separately')
(P/'compile-request.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
u.log('ARCANE_POMMELS_COMPILE_RETURN '+request['returned'])
