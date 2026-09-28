import unreal as u
e=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if e.get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('Requested PIE stop to save the user-approved hub layout; editor stays open.')
