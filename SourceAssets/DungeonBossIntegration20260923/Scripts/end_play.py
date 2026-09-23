import unreal as u
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('END_PLAY_REQUESTED for authorized dungeon integration')
else:print('No play session')
