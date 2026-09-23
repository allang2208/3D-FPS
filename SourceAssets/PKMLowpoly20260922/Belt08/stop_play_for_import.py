import unreal as u
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
print('Requested end of PIE for PKM asset saving; editor remains open.')
