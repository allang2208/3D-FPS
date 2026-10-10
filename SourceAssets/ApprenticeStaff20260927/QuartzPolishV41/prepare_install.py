"""End PIE under the user's existing installation authorization; keep UE open."""
import json
from pathlib import Path
import unreal as u

editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
playing = editor.is_in_play_in_editor()
if playing:
    editor.editor_request_end_play()
Path(__file__).with_name('installation-preparation.json').write_text(json.dumps(
    dict(was_playing=playing,end_play_requested=playing)),encoding='utf-8')
print('QUARTZ_V41_PREPARED end_play_requested='+str(playing))
