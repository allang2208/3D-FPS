"""Apply the rune-sword-only cooldown trait through the existing editor."""
from pathlib import Path
import unreal

if Path(unreal.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_game_world() or editor.get_editor_world()
print('HIGHLAND_COOLDOWN_OWNERSHIP_COMPILE_BEGIN')
unreal.SystemLibrary.execute_console_command(world, 'LiveCoding.CompileSync')
print('HIGHLAND_COOLDOWN_OWNERSHIP_COMPILE_RETURNED; compiler log determines completion')
