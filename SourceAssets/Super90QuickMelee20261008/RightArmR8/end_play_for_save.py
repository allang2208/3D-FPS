"""End the active preview only so the completed animation assets can be saved."""
import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('SUPER90_R8_END_PLAY_REQUESTED_FOR_ASSET_SAVE')
else:
    print('SUPER90_R8_EDITOR_READY_FOR_ASSET_SAVE')
