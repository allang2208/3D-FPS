"""Apply the RSH ADS implementation through the editor that is already running."""
import unreal as u
from pathlib import Path
if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Unexpected project')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
print('RSH12_COCK_COMPILE_BEGIN',flush=True)
u.SystemLibrary.execute_console_command(world,'LiveCoding.CompileSync')
print('RSH12_COCK_COMPILE_RETURNED; read this compilation result before publishing',flush=True)
