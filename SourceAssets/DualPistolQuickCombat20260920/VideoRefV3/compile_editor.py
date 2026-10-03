"""Apply the existing-function edits with Live Coding; do not start PIE."""
import datetime
import json
from pathlib import Path
import unreal as u

started = datetime.datetime.now().isoformat()
u.log('DUAL_VIDEO_V3_COMPILE_BEGIN ' + started)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world, 'LiveCoding.CompileSync')
finished = datetime.datetime.now().isoformat()
(Path(__file__).parent / 'compile-request.json').write_text(json.dumps({
    'started': started, 'returned': finished, 'command': 'LiveCoding.CompileSync',
    'result': 'Read the corresponding build output; command return is not a success result',
    'testing': 'Not performed; user testing'
}, indent=2), encoding='utf-8')
u.log('DUAL_VIDEO_V3_COMPILE_RETURN ' + finished)
