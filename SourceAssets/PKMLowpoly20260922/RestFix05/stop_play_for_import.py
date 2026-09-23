import unreal as u
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
print('Requested end of play for PKM asset reimport; editor remains open.')
