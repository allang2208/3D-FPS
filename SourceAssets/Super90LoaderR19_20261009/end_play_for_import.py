"""End the existing PIE world so the requested animation packages can be saved."""
import unreal as u
subsystem=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if subsystem and subsystem.get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print('Requested end of existing PIE for Super90 asset import; editor remains open.')
else:
    print('No PIE world; editor remains open.')
