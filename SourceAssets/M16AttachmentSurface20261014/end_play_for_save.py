import unreal as u
sub=u.get_editor_subsystem(u.LevelEditorSubsystem)
if sub.is_in_play_in_editor():
 sub.editor_request_end_play()
 print('Requested end of the current PIE session for the authorized asset repair.')
else:print('PIE is already stopped.')
