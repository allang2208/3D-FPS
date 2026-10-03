"""Apply existing C++ function changes without restarting the editor."""
import datetime
import unreal as u
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.log('SWORD_OVERHEAD_IMPACT_V2_COMPILE_BEGIN '+datetime.datetime.now().isoformat())
u.SystemLibrary.execute_console_command(world,'LiveCoding.CompileSync')
u.log('SWORD_OVERHEAD_IMPACT_V2_COMPILE_RETURN '+datetime.datetime.now().isoformat())
