from pathlib import Path
import unreal as u
if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():
 raise RuntimeError('Unexpected editor project')
print('UPPERCUT_V14_COMPILE_BEGIN')
u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'LiveCoding.CompileSync')
print('UPPERCUT_V14_COMPILE_RETURNED; compiler output determines completion')
