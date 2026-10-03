"""Apply only implementation changes to the editor already running for FPSGAME."""
from pathlib import Path
import unreal as u

if Path(u.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
print('TANGDAO_NATIVE_RUNES_COMPILE_BEGIN')
u.SystemLibrary.execute_console_command(editor.get_editor_world(), 'LiveCoding.CompileSync')
print('TANGDAO_NATIVE_RUNES_COMPILE_RETURNED; compiler log determines success')
