"""Read only the editor state needed to choose a safe integration path."""
import unreal as u,json
from pathlib import Path
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_editor_world() if editor else None
report=dict(world=world.get_path_name() if world else None,playing=bool(editor and editor.get_game_world()),
 dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
Path('D:/FPS3D/FPSGAME/SourceAssets/CyberpunkBayBuildings20261022/editor-context.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
