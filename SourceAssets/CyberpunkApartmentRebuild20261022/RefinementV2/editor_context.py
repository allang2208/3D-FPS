from pathlib import Path
import json,unreal as u
r=Path(__file__).resolve().parent
e=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=e.get_editor_world() if e else None
game=e.get_game_world() if e else None
result=dict(project=u.Paths.project_dir(),world=w.get_path_name() if w else None,
    game=game.get_path_name() if game else None,
    dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(r/'editor_context.json').write_text(json.dumps(result,indent=2),encoding='utf8')
u.log('APARTMENT_CONTEXT '+json.dumps(result))
