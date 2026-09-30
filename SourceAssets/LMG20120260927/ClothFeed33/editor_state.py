import unreal as u,json
from pathlib import Path
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
game=editor.get_game_world()
info={'game_world':game.get_path_name() if game else None,'dirty_content_packages':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
(Path(__file__).parent/'editor_state.json').write_text(json.dumps(info,indent=2))
print('CLOTH33_EDITOR_STATE',json.dumps(info),flush=True)
