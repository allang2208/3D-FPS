import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
 print('Requested end of PIE for idle asset edit; editor kept open.')
else:print('No PIE running; ready for idle asset edit.')
