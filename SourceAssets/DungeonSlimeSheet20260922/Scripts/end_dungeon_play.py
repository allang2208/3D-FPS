"""Use the user's standing permission to end this dungeon's play for integration only."""
import unreal as u
game=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
name=game.get_path_name() if game else ''
del game
if not name:print('NO_PLAY')
elif 'L_Dungeon_AuthoredExpansion' in name:
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('END_AUTHORED_DUNGEON_PLAY_REQUESTED')
else:raise RuntimeError('Preserved running play in another map: '+name)
