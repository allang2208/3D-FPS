"""Run only after the user elects to end PIE for this map save."""
from pathlib import Path
import json
import unreal as u
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
game=s.get_game_world()
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if set(dirty)-{'/Game/GameMaps/L_CyberpunkApartment'}:
    raise RuntimeError('Preserve unrelated unsaved maps: '+str(dirty))
report=dict(game_world=game.get_path_name() if game else None,dirty_maps=dirty,requested=bool(game))
if game:u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
(R/'end-play.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('END_PLAY_FOR_APPROVED_SAVE',json.dumps(report))
