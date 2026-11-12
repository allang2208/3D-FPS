import unreal as u,json
from pathlib import Path
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
state={'game_world':world.get_path_name() if world else None,'dirty':[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
(Path(__file__).parent/'editor_state.json').write_text(json.dumps(state,indent=2))
print(json.dumps(state))
