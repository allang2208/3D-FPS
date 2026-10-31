from pathlib import Path
import json,unreal as u
r=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=ed.get_editor_world();g=ed.get_game_world()
d=dict(world=w.get_path_name() if w else None,game=g.get_path_name() if g else None,dirty_maps=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],dirty_content=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
(r/'editor_state.json').write_text(json.dumps(d,indent=2))
print(json.dumps(d))
