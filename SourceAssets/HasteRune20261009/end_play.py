import unreal as u
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    u.EditorLevelLibrary.editor_end_play()
    print('HASTE_RUNE_USER_AUTHORIZED_END_PLAY_REQUESTED')
else:
    print('HASTE_RUNE_EDITOR_ALREADY_IDLE')
