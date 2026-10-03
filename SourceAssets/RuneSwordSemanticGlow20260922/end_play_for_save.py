"""End PIE only because the editor refuses to save this material during play."""
import unreal as u
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('END_PLAY_REQUESTED_FOR_MATERIAL_SAVE')
else:
    print('EDITOR_ALREADY_OUT_OF_PLAY')
