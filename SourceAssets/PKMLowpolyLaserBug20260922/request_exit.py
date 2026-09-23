"""Ask the editor to save its packages and exit, so a build can replace the module.

Used only for the build step: UnrealEditor-FPSGAME.dll is loaded by the editor, so
a link cannot replace it until the process exits. This requests a normal shutdown
(not a kill) so unsaved work is handled by the editor's own save prompts.
"""
import unreal as u

subsystem = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if subsystem is None:
    raise RuntimeError('UnrealEditorSubsystem unavailable')
u.log('PKM_REQUEST_EDITOR_EXIT')
# This engine build exposes the exit through SystemLibrary, not the editor
# subsystem; it closes the editor normally, so its own save prompts still apply.
u.SystemLibrary.quit_editor()
print('exit requested')
