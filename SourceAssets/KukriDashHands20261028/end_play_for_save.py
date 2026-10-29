"""End active PIE for the pending animation save; keep the editor open."""
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
if Path(u.Paths.get_project_file_path()).resolve()!=ROOT/'FPSGAME.uproject':raise RuntimeError('Wrong project')
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('PIE_END_REQUESTED_FOR_ANIMATION_SAVE')
else:print('PIE_ALREADY_STOPPED')
