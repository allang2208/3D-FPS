"""Enable UE's existing Live Coding module for this editor session only."""
import unreal as u
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
# Engine console command calls EnableForSession, without saving preferences.
u.SystemLibrary.execute_console_command(world,'LiveCoding')
u.log('MELEE_SPRINT_LIVE_SESSION_ENABLE_REQUESTED')
