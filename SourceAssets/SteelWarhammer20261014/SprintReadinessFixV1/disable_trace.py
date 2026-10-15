"""Turn off the temporary sprint diagnostic after the user's recovery report."""
import unreal as u
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=sub.get_game_world() or sub.get_editor_world()
u.SystemLibrary.execute_console_command(world,'fps.Tool.SprintTrace 0')
print('WARHAMMER_SPRINT_TRACE_DISABLED')
