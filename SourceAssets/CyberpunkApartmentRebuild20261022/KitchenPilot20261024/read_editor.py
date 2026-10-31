"""Read-only editor connection / dirty state; no save, no new editor process."""
from pathlib import Path
import unreal as u,json,traceback
R=Path(__file__).resolve().parent
try:
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    row=dict(pie=bool(ed and ed.get_game_world()),dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],dirty_packages=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],map=u.EditorLoadingAndSavingUtils.get_current_map().get_path_name() if hasattr(u.EditorLoadingAndSavingUtils,'get_current_map') else 'unknown')
    print('KITCHEN_EDITOR_STATE '+json.dumps(row))
    (R/'editor-state.json').write_text(json.dumps(row,indent=2),encoding='utf8')
except Exception:print(traceback.format_exc())
