"""End the current PIE session so its editor can save the requested apartment replacement."""
import unreal as u,json
from pathlib import Path
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem);game=s.get_game_world()
report=dict(game_world=game.get_path_name() if game else None,dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],dirty_content=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
if report['dirty_maps']:raise RuntimeError('Preserve unrelated unsaved map work: '+str(report['dirty_maps']))
if game:u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
(R/'end-play.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('END_PIE_REQUESTED_FOR_APARTMENT_INSTALL',report)
