import unreal as u,json
from pathlib import Path
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
r={'dirty':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'editor_world':s.get_editor_world().get_path_name() if s.get_editor_world() else None,'game_world':s.get_game_world().get_path_name() if s.get_game_world() else None}
Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KClosure20261018/Reports/editor-state.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
