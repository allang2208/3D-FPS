"""Read only the editor state needed to safely save the pending new map."""
from pathlib import Path
import json,unreal as u
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
state=dict(project=u.Paths.project_dir(),world=world.get_path_name() if world else None,
    pie=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(Path(__file__).resolve().parent/'Receipts/editor-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
print('RECEPTION_SAVE_CONTEXT',state)
