"""End PIE for the authorized asset/native handoff, preserving unsaved assets."""
import json
from pathlib import Path
import unreal as u
if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project; editor state preserved')
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
root=Path('D:/FPS3D/FPSGAME/SourceAssets/FreightEncounter20261014/Receipts')
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    report=dict(stage='end_play_requested')
else:
    maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    content=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    report=dict(stage='editor_ready',unsaved_maps=maps,unsaved_content=content)
(root/'editor-handoff.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('FREIGHT_HANDOFF '+json.dumps(report,ensure_ascii=False))
