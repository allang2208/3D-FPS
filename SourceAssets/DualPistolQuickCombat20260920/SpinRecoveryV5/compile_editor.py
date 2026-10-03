"""Apply existing-function changes with Live Coding; no game/test launch."""
import datetime,json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
started=datetime.datetime.now().isoformat()
u.log('DUAL_SPIN_RECOVERY_COMPILE_BEGIN '+started)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'LiveCoding.CompileSync')
(P/'compile-request.json').write_text(json.dumps({'started':started,'returned':datetime.datetime.now().isoformat(),
    'command':'LiveCoding.CompileSync','result':'Read matching build output; command return alone is not success','runtime_tested':False},indent=2))
u.log('DUAL_SPIN_RECOVERY_COMPILE_RETURN')
