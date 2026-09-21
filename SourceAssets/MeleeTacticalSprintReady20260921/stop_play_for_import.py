"""End active play so this task's sprint animation assets can be written."""
import unreal as u
editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor.is_in_play_in_editor():
    editor.editor_request_end_play()
    u.log('MELEE_SPRINT_V4_END_PLAY_REQUESTED')
else:
    u.log('MELEE_SPRINT_V4_EDITOR_READY')
