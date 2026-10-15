"""Read the current editor's save state before updating its loaded DLL."""
import json, os
from pathlib import Path
import unreal as u

p = Path(__file__).resolve().parent
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
state = {
    'editor_pid': os.getpid(),
    'game_world': world.get_path_name() if world else None,
    'dirty_content': [x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    'dirty_maps': [x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
}
(p / 'editor_build_state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
print(json.dumps(state))
