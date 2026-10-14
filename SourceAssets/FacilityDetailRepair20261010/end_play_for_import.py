"""Finish the play session the user confirmed ending before the final asset save."""
import unreal as u
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
playing=level.is_in_play_in_editor()
if playing:level.editor_request_end_play()
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print('FINAL_IMPORT_PLAY_STATE',playing,world.get_path_name() if world else None,'end_requested',playing)
