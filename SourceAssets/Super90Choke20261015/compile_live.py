"""Compile existing-layout changes in the editor that is already running."""
import unreal as u
from pathlib import Path
if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
print('SHOTGUN_CHOKE_LIVE_COMPILE_BEGIN',flush=True)
u.SystemLibrary.execute_console_command(editor.get_game_world() or editor.get_editor_world(),'LiveCoding.CompileSync')
print('SHOTGUN_CHOKE_LIVE_COMPILE_RETURNED',flush=True)
