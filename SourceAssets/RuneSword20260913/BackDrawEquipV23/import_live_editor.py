"""Apply the equip asset in its owning editor once the current PIE ends."""
import runpy
from pathlib import Path
import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End the active PIE session before importing the equip animation.')
runpy.run_path(str(Path(__file__).with_name('import_equip.py')),run_name='__main__')
