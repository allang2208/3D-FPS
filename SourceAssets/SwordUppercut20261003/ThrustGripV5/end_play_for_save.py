import unreal as u
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
print('Requested end of current PIE for animation asset saving; editor stays open.')
