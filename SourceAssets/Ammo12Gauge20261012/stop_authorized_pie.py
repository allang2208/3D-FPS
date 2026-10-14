"""End the currently running PIE session, authorized by the user for final ammo saves."""
import unreal

editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.log('AMMO_SAVE_PIE_END_REQUESTED')
else:
    unreal.log('AMMO_SAVE_PIE_ALREADY_STOPPED')
