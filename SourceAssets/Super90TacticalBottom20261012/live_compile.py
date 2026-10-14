"""Compile the existing-function edits in the already-running editor."""
from pathlib import Path
import unreal as u
if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
print('SUPER90_TACTICAL_COMPILE_BEGIN',flush=True)
u.SystemLibrary.execute_console_command(editor.get_game_world() or editor.get_editor_world(),'LiveCoding.CompileSync')
print('SUPER90_TACTICAL_COMPILE_RETURNED',flush=True)
