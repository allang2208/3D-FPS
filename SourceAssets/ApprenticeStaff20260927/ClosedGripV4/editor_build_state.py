"""Read only the editor state needed for a safe native build."""
import json
from pathlib import Path
import unreal as u
root=Path(r'D:/FPS3D/FPSGAME/SourceAssets/ApprenticeStaff20260927/ClosedGripV4')
state={'dirty_content':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
       'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
       'playing':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()}
(root/'editor-build-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(state,ensure_ascii=False))
