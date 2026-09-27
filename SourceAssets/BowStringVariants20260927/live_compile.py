"""Compile the shared speed label in an already running editor; never start PIE."""
from pathlib import Path
import unreal
if Path(unreal.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('PIE active: preserve current game')
print('BOW_STRING_VOCABULARY_COMPILE_BEGIN')
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'LiveCoding.CompileSync')
print('BOW_STRING_VOCABULARY_COMPILE_RETURNED; see compiler log for result')
