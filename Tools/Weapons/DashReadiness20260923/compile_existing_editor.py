"""Compile readiness logic in the existing editor without starting a game."""
from pathlib import Path
import unreal

if Path(unreal.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
# No reflected declarations, instance layout, assets, or constructor defaults
# changed. The new inline reset only writes the existing readiness timer.
print('DASH_READINESS_COMPILE_BEGIN')
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'LiveCoding.CompileSync')
print('DASH_READINESS_COMPILE_RETURNED; compiler output determines completion')
