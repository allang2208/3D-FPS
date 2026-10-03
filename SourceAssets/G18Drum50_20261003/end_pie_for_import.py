"""User explicitly authorized ending the current PIE for this import batch."""
import unreal
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor.editor_request_end_play()
print('G18_DRUM50_REQUESTED_END_PIE',flush=True)
