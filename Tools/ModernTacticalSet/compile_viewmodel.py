"""Compile the body-only shirt policy in the already-running editor."""
import unreal as u
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'LiveCoding.Compile')
print('TS01_LIVE_COMPILE_REQUESTED')
