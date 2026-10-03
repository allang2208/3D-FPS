"""End an existing play session only when needed for animation asset saving."""
import unreal as u

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    u.log('MUTANT3_FORWARD_FLIP_SAVE_PREPARATION: existing PIE end requested; editor retained')
else:
    u.log('MUTANT3_FORWARD_FLIP_SAVE_PREPARATION: editor ready for asset saving')
