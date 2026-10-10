"""Read only the current play state needed for this installation."""
import unreal as u
from pathlib import Path
import json
playing=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
Path(__file__).with_name('install-state.json').write_text(json.dumps({'playing':playing}),encoding='utf-8')
print('STAFF_V37_INSTALL_STATE playing='+str(playing))
