"""Compile existing function changes in the editor already running for FPSGAME."""
import unreal as u
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
print('XUANCHI_RUNE_GUARD_COMPILE_BEGIN',flush=True)
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'LiveCoding.CompileSync')
print('XUANCHI_RUNE_GUARD_COMPILE_RETURNED; compiler log determines success',flush=True)
