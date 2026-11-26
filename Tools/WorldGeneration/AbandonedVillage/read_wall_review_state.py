import json
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateHillsVillage/WallReview20261114')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world,game=editor.get_editor_world(),editor.get_game_world()
report=dict(editor_world=world.get_path_name() if world else None,game_world=game.get_path_name() if game else None,
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
report['capture_api']={name:str(getattr(u.RenderingLibrary,name).__doc__) for name in
    ['create_render_target2d','export_render_target','draw_material_to_render_target']}
report['capture_doc']=str(u.SceneCaptureComponent2D.capture_scene.__doc__)
(out/'editor-state.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
