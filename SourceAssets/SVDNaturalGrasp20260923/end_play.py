import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
 print('SVD_NATURAL_USER_AUTHORIZED_END_PLAY_REQUESTED')
else:print('SVD_NATURAL_NO_ACTIVE_PLAY')
