"""End only play, under the existing SVD import authorization; keep the editor."""
import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('SVD_HAND_END_PLAY_REQUESTED_FOR_IMPORT')
else:
    print('SVD_HAND_NO_PLAY_SESSION')
