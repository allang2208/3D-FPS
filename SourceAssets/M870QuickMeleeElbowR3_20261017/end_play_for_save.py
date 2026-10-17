"""End only the existing PIE session so loaded animation assets can be saved."""
import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('M870_R3_END_EXISTING_PIE_REQUESTED_FOR_ASSET_SAVE')
else:
    print('M870_R3_NO_ACTIVE_PIE')
