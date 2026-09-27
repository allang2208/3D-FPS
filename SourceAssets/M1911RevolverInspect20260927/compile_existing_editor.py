"""Compile the function-only inspect rollback in the existing UE session."""
from datetime import datetime
from pathlib import Path
import json
import unreal as u

if Path(u.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
started = datetime.now().isoformat()
u.log('M1911_ORIGINAL_INSPECT_COMPILE_BEGIN ' + started)
u.SystemLibrary.execute_console_command(editor.get_game_world() or editor.get_editor_world(), 'LiveCoding.CompileSync')
Path(__file__).with_name('compile-request.json').write_text(json.dumps({
    'started': started, 'returned': datetime.now().isoformat(), 'command': 'LiveCoding.CompileSync',
    'status': 'Compiler log determines success; not a runtime test'}, indent=2))
u.log('M1911_ORIGINAL_INSPECT_COMPILE_RETURNED')
