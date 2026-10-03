"""End an existing play session only to permit the requested production import."""
import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('PIT_VIPER_FIRE_IMPORT_END_PLAY_REQUESTED', flush=True)
else:
    print('PIT_VIPER_FIRE_IMPORT_NO_PLAY_SESSION', flush=True)
