"""End the current PIE run with the user's explicit approval; keep UE open."""
import unreal as u
if u.EditorLevelLibrary.get_game_world():
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
 print('RSH12_USER_APPROVED_PIE_END_REQUESTED',flush=True)
else:print('RSH12_PIE_ALREADY_ENDED',flush=True)
