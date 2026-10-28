"""Read only the state needed to safely finish imports and a regular Editor build."""
import json
from pathlib import Path
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriFinalIntegration20261026')
state={
 'dirty_content_packages':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
 'dirty_map_packages':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
 'pie_worlds':[w.get_path_name() for w in u.EditorLevelLibrary.get_pie_worlds(False)],
}
(P/'Receipts/editor-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('KUKRI_BUILD_PRECONDITIONS '+json.dumps(state,ensure_ascii=False))
