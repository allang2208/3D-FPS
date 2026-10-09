"""End the active preview so the prepared researcher assets can be saved."""
import unreal as u
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('RESEARCHER_REACTION_IMPORT_END_PLAY_REQUESTED')
else:
    print('RESEARCHER_REACTION_IMPORT_EDITOR_READY')
