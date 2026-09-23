import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
 print('PSO_USER_AUTHORIZED_END_PLAY_REQUESTED')
else:print('PSO_NO_ACTIVE_PLAY')
