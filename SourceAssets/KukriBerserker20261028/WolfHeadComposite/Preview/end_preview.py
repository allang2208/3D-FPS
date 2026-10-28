import unreal as u
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor.is_in_play_in_editor():editor.editor_request_end_play()
print('BERSERKER_HUD_PREVIEW_ENDED_EDITOR_PRESERVED')
