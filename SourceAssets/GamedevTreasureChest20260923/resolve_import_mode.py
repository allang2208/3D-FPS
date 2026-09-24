import unreal as u
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
game=editor.get_game_world()
print('TREASURE_IMPORT_CONTEXT',game.get_path_name() if game else None,level.is_in_play_in_editor())
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('TREASURE_REPAIR_END_PLAY_REQUESTED')
