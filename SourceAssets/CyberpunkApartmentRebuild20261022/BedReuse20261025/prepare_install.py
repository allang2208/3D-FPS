"""Report editor state for the requested scoped bed replacement."""
from pathlib import Path
import json
import unreal as u
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=s.get_editor_world();game=s.get_game_world()
report=dict(editor_world=world.get_path_name() if world else None,
            game_world=game.get_path_name() if game else None,
            dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(R/'editor-state.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
