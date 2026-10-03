import unreal as u
from pathlib import Path
expected=Path('D:/FPS3D/FPSGAME/FPSGAME.uproject')
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=expected:
    raise RuntimeError('M07 asset-save operation belongs to FPSGAME')
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
print('End PIE requested for M07 asset saving; editor remains open')
