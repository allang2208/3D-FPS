"""Request the normal Slate close only when no unsaved work or running PIE remains."""
import json
from pathlib import Path
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriFinalIntegration20261026')
state={
 'dirty_content_packages':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
 'dirty_map_packages':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
 'pie_worlds':[w.get_path_name() for w in u.EditorLevelLibrary.get_pie_worlds(False)],
}
(P/'Receipts/before-normal-close.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
if any(state.values()):raise RuntimeError('Editor retained: unsaved work or active play; '+json.dumps(state,ensure_ascii=False))
u.log('KUKRI_NORMAL_EDITOR_CLOSE_REQUESTED_FOR_BASE_DLL_BUILD')
u.SystemLibrary.execute_console_command(None,'CLOSE_SLATE_MAINFRAME')
