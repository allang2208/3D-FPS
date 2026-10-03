"""End existing PIE for asset authoring; never starts a play session or closes the editor."""
import unreal as u

u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
print('CLEARWATER_AUTHORING_END_PLAY_REQUESTED')
