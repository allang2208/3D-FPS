"""Present the saved new room in the editor; preserve active play and unsaved maps."""
import unreal as u
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
if UE.get_game_world():
    print('ROOMS_SAVED_PRESENTATION_DEFERRED: active play preserved; re-enter Authored Expansion to load the new rooms')
elif u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    print('ROOMS_SAVED_PRESENTATION_DEFERRED: unsaved map preserved')
else:
    if not ED.load_level('/Game/GameMaps/L_Dungeon_AuthoredExpansion'):raise RuntimeError('Could not open saved rooms')
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(2400,-1930,259),u.Rotator(pitch=-3,yaw=-67,roll=0))
    print('ROOM_SHELL_MAP_OPENED_AT_DISTRIBUTION_ROOM')
