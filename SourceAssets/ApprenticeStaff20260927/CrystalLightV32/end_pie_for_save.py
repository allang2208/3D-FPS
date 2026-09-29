"""End the running game only because material save is blocked during PIE."""
import unreal as u
editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor.is_in_play_in_editor():
    editor.editor_request_end_play()
    print('Requested PIE end for saving the crystal material; editor remains open.')
else:
    print('PIE already stopped.')
