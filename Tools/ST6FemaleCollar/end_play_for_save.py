"""End existing PIE so the authorized clothing assets can be saved."""
import unreal as u
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('ST6_FEMALE_END_PLAY_REQUESTED')
else:
    print('ST6_FEMALE_ASSET_SAVE_AVAILABLE')
