"""End the active preview so the authorized face material can be saved."""
import unreal as u
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
print('JASON_FACE_EDIT_END_PLAY_REQUESTED')
