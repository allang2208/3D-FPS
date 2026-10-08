"""Build the common melee icon selection change in the already running editor."""
from pathlib import Path
from datetime import datetime,timezone
import json,unreal as u
P=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=P.parents[1]:raise RuntimeError('Unexpected project')
receipt={'started_utc':datetime.now(timezone.utc).isoformat(),'command':'LiveCoding.CompileSync',
    'scope':'Common melee option icon selection','game_tested':False}
(P/'compile_request.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
print('SHARED_POMMEL_ICON_NATIVE_COMPILE_BEGIN',flush=True)
u.SystemLibrary.execute_console_command(world,'LiveCoding.CompileSync')
receipt['returned_utc']=datetime.now(timezone.utc).isoformat()
(P/'compile_request.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print('SHARED_POMMEL_ICON_NATIVE_COMPILE_RETURNED; compiler log determines success',flush=True)
