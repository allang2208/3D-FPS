"""Compile the short bipod clock and optic alias in the existing editor."""
import json
from pathlib import Path
from datetime import datetime
import unreal as u
O=Path(__file__).resolve().parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.log('M24_QUICK048_COMPILE_BEGIN')
started=datetime.now().isoformat()
u.SystemLibrary.execute_console_command(world,'LiveCoding.CompileSync')
(O/'live_compile_request.json').write_text(json.dumps({'started':started,'returned':datetime.now().isoformat(),
    'command':'LiveCoding.CompileSync','runtime_tested':False,'status':'See compiler output for completion'},indent=2))
u.log('M24_QUICK048_COMPILE_RETURNED')
