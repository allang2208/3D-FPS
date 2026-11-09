"""Apply the shared scope eye relief in the already-open editor."""
import unreal as u
import json
from pathlib import Path
from datetime import datetime

r = Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve() != r.parents[2]:
    raise RuntimeError('Unexpected editor project')
pie_active = u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
started = datetime.now().isoformat()
u.log('SCOPE_EYE_RELIEF_COMPILE_BEGIN ' + started)
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_game_world() if pie_active else editor.get_editor_world()
u.SystemLibrary.execute_console_command(world, 'LiveCoding.CompileSync')
(r / 'live_compile_request.json').write_text(json.dumps(dict(
    started=started, returned=datetime.now().isoformat(),
    command='LiveCoding.CompileSync', pie_active_at_request=pie_active,
    base_editor_dll_updated=False, runtime_tested=False,
    status='Compiler log determines success'), indent=2))
u.log('SCOPE_EYE_RELIEF_COMPILE_RETURNED')
