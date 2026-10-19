import json
from pathlib import Path
import unreal as u
r={'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'dirty_content':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'pie':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'quit_api':[n for n in dir(u.SystemLibrary) if 'quit' in n]}
Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018/StairRepair20261019/editor-unsaved-state.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
