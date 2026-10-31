import unreal as u
sub=u.get_editor_subsystem(u.LevelEditorSubsystem)
sub.editor_request_end_play()
print('END_PLAY_REQUESTED_EDITOR_PRESERVED')
