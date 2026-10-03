"""Complete the PIE stop the user has requested before saving the final joints."""
import os,unreal as u
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print('PKM_SAVE_EDITOR_STATE',os.getpid(),level.is_in_play_in_editor(),world.get_path_name() if world else None)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('PKM_USER_REQUESTED_PIE_STOP_QUEUED')
