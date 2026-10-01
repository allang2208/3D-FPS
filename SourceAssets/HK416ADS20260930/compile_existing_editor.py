import unreal as u,json
from pathlib import Path
from datetime import datetime
o=Path(__file__).parent
subsystem=u.get_editor_subsystem(u.UnrealEditorSubsystem)
u.log('HK416_IRON_SIGHT_COMPILE_BEGIN')
started=datetime.now().isoformat()
u.SystemLibrary.execute_console_command(subsystem.get_game_world() or subsystem.get_editor_world(),'LiveCoding.CompileSync')
(o/'compile_request.json').write_text(json.dumps({'started':started,'returned':datetime.now().isoformat(),'command':'LiveCoding.CompileSync','status':'Read compiler output for result.'},indent=2))
u.log('HK416_IRON_SIGHT_COMPILE_RETURNED')
