"""End the existing PIE session so the requested animation assets can be saved."""
import unreal as u
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('SUPER90_IMPORT_END_PIE_REQUESTED',flush=True)
