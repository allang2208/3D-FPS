"""Compile and apply the action-priority update without starting gameplay."""
from pathlib import Path
import unreal

if Path(unreal.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world() is not None:
    raise RuntimeError('The editor is running PIE; keep that game session intact')
print('ACTION_PRIORITY_COMPILE_BEGIN')
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'LiveCoding.CompileSync')
print('ACTION_PRIORITY_COMPILE_RETURNED; compiler log determines completion')
