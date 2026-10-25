"""End the current FPSGAME preview so its material can be saved in the editor."""
from pathlib import Path
import unreal as u
if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME'):
    raise RuntimeError('Wrong editor project')
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor.is_in_play_in_editor():
    editor.editor_request_end_play()
    print('Requested end of current PIE; editor remains open')
else:
    print('PIE already stopped; editor remains open')
