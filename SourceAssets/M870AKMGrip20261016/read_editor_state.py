import unreal as u,json
from pathlib import Path
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
state={'pie_active':editor.is_in_play_in_editor(),'game_world':str(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'asset_import_started':False}
(Path(__file__).parent/'editor_state.json').write_text(json.dumps(state,indent=2));print(json.dumps(state))
