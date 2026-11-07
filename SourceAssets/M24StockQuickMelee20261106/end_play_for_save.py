"""User approved ending PIE to save the completed M24 motion resources."""
import unreal as u
if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
    print('M24_NO_EDITOR_SESSION; BACKGROUND_SAVE_READY')
else:
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor.is_in_play_in_editor():
        editor.editor_request_end_play()
        print('M24_END_PLAY_REQUESTED_FOR_ASSET_SAVE')
    else:
        print('M24_EDITOR_READY_FOR_ASSET_SAVE')
