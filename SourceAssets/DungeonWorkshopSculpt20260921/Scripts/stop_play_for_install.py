"""User explicitly authorized ending this running session to install the workshop revision."""
import unreal as u
sub=u.get_editor_subsystem(u.LevelEditorSubsystem)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    sub.editor_request_end_play();print('WORKSHOP_USER_AUTHORIZED_END_PLAY_REQUESTED')
else:print('WORKSHOP_PLAY_ALREADY_ENDED')
