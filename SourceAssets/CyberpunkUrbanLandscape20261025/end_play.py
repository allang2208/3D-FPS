import unreal as u,json
from pathlib import Path
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);game=editor.get_game_world();world=editor.get_editor_world()
report=dict(editor_world=world.get_path_name() if world else None,game_world=game.get_path_name() if game else None,dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
report['in_pie']=level.is_in_play_in_editor()
if game or report['in_pie']:
    level.editor_request_end_play();report['end_play_requested']=True
else:report['end_play_requested']=False
(Path(__file__).resolve().parent/'end_play.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('URBAN_END_PLAY',report,flush=True)
