import unreal as u
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print('SUPER90_R8_IMPORT_STATE',level.is_in_play_in_editor(),str(world))
