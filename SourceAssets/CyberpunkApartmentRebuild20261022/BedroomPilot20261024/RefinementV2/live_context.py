import unreal as u,json
from pathlib import Path
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
editor=s.get_editor_world();game=s.get_game_world()
report=dict(editor_world=editor.get_path_name() if editor else None,game_world=game.get_path_name() if game else None,
            dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(R/'live-context.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
