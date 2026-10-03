"""Compile the existing sprint-return function in the already running editor."""
from pathlib import Path
import unreal

if Path(unreal.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
# This revision only retimes an existing function; no object layout or asset
# change requires stopping the user's running game.
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
print('MELEE_SPRINT_RETURN_COMPILE_BEGIN')
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'LiveCoding.CompileSync')
print('MELEE_SPRINT_RETURN_COMPILE_RETURNED; completion is recorded by Live Coding')
