import os
import json
import unreal as u
print(json.dumps({'pid': os.getpid(), 'command_line': u.SystemLibrary.get_command_line(),
    'pie': u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
    'log_directory': u.Paths.project_log_dir()}))
