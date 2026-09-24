"""Rebuild only splash assets; preserve the accepted ripple material."""
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if root!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('End PIE before replacing the splash emitter graphs.')
script=root/'Tools/Fluids/author_river_pilot.py'
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),
     {'__file__':str(script),'__name__':'__main__','RIVER_SPLASH_ONLY':True})
