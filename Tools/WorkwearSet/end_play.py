"""Run only after the user explicitly authorizes ending their current PIE."""
import unreal as u
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level and level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('WORKWEAR_REQUESTED_END_PLAY_EDITOR_RETAINED',flush=True)
else:
    print('WORKWEAR_NO_ACTIVE_PLAY',flush=True)
