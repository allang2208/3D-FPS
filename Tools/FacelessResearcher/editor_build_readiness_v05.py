"""Read current unsaved packages before the required native editor rebuild."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V05')
report={'content':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    'maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()}
(ROOT/'editor_build_readiness.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M05_EDITOR_BUILD_READINESS '+json.dumps(report),flush=True)
