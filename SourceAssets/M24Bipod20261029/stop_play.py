"""End the current PIE session so the requested M24 animation assets can be saved."""
import unreal as u
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
print('M24_ASSET_SAVE_END_PLAY_REQUESTED')
