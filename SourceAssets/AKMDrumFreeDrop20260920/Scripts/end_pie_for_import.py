"""End FPSGAME PIE so this task can import its prepared animation assets."""
import unreal as u
from pathlib import Path
O=Path(__file__).resolve().parents[1]
if Path(u.Paths.get_project_file_path()).resolve()!=O.parents[1]/'FPSGAME.uproject':raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
 print('PIE_END_REQUESTED')
else:print('PIE_ALREADY_STOPPED')
