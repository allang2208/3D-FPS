"""Build the dash forward step in the open editor; never starts PIE."""
from datetime import datetime
from pathlib import Path
import json
import unreal as u

editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:
    raise RuntimeError('PIE is active; keep it intact and compile after it ends.')
world = editor.get_editor_world()
started = datetime.now().isoformat()
u.log('DASH_ATTACK_ONE_METRE_COMPILE_BEGIN ' + started)
u.SystemLibrary.execute_console_command(world, 'LiveCoding')
u.SystemLibrary.execute_console_command(world, 'LiveCoding.CompileSync')
out = Path(u.Paths.project_saved_dir()) / 'DashAttackForward20260922'
out.mkdir(parents=True, exist_ok=True)
(out / 'compile-request.json').write_text(json.dumps({
    'started': started, 'returned': datetime.now().isoformat(),
    'command': 'LiveCoding.CompileSync',
    'result': 'Compiler output determines success; command return alone is not confirmation.',
    'runtime_tests': 'Not run; user will test.'
}, indent=2), encoding='utf-8')
u.log('DASH_ATTACK_ONE_METRE_COMPILE_RETURN')
