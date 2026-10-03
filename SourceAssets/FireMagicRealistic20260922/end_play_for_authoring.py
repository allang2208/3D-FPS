import unreal as u
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    u.EditorLevelLibrary.editor_end_play()
    print('Requested end of active PIE for asset authoring; editor stays open.')
else:
    print('No active play world; editor stays open.')
