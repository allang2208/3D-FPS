"""Compile inventory logic in the existing editor; do not start PIE or tests."""
from pathlib import Path
import unreal

if Path(unreal.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
# Only implementation and inline solver changes; no reflected layout or assets.
print('EQUIPMENT_AUTO_ORIENTATION_COMPILE_BEGIN')
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'LiveCoding.CompileSync')
print('EQUIPMENT_AUTO_ORIENTATION_COMPILE_RETURNED; compiler output determines completion')
