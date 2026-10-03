"""End the current preview so changed action state can be reinstanced safely."""
from pathlib import Path
import unreal
if Path(unreal.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
print('Requested end of game preview for action-priority compilation')
