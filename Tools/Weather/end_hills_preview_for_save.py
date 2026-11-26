import unreal as u

game = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if game:
    if 'L_TemperateHills_Initial' not in game.get_path_name():
        raise RuntimeError('An unrelated game preview is active; left it running')
    u.EditorLevelLibrary.editor_end_play()
    print('Requested end of the hills preview for its map save')
else:
    print('No active preview')
