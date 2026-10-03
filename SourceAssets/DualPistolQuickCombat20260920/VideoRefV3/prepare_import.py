"""End active PIE only when needed to save the requested animation assets."""
import unreal as u

level = u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    u.log('DUAL_VIDEO_V3_END_PLAY_REQUESTED_FOR_ASSET_SAVE')
