"""End PIE normally so the editor's static-mesh authoring APIs can run."""
import json
import os
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
running = editor.get_game_world() is not None
if running:
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
state = {'editor_pid': os.getpid(), 'end_play_requested': running,
         'reason': 'StaticMeshEditorSubsystem LOD build settings reject PIE'}
(P / 'end-play-for-import.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
print(json.dumps(state))
