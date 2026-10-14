from pathlib import Path
import unreal as u,json
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
r=dict(editor=ed.get_editor_world().get_path_name() if ed.get_editor_world() else None,game=ed.get_game_world().get_path_name() if ed.get_game_world() else None,dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(Path(__file__).resolve().parent/'Receipts/state.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps(r))
