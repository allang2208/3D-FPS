import unreal as u
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if not editor.is_in_play_in_editor():editor.editor_request_begin_play()
print('BERSERKER_HUD_GAME_PREVIEW_REQUESTED')
