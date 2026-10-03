"""End the main project's active PIE so its attack asset can be saved."""
from pathlib import Path
import unreal as u

project = Path(__file__).resolve().parents[3]
if Path(u.Paths.project_dir()).resolve() != project:
    raise RuntimeError('Wrong project; PIE preserved')
if u.EditorLevelLibrary.get_game_world() is not None:
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('RELATED_PIE_END_REQUESTED_EDITOR_PRESERVED', flush=True)
else:
    print('EDITOR_READY_FOR_ANIMATION_SAVE', flush=True)
