"""Read only the state needed to apply this task's build and catalog safely."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
state=dict(project=u.Paths.project_dir(),pie=bool(ue.get_game_world()),world=ue.get_editor_world().get_path_name(),
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_content=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
(ROOT/'Receipts/editor-state.json').write_text(json.dumps(state,indent=2))
print(json.dumps(state))
