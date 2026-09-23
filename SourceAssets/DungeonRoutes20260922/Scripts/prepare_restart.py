"""Finish this batch's material saves, then normally close a clean project for native build."""
import unreal as u,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
info=dict(pid=os.getpid(),world=UE.get_editor_world().get_path_name() if UE.get_editor_world() else None,game=UE.get_game_world().get_path_name() if UE.get_game_world() else None,dirty=[p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())])
(ROOT/'Receipts/editor-state.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
