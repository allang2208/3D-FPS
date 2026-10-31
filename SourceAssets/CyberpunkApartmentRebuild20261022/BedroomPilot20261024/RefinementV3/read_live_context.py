import unreal as u,json
from pathlib import Path
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
ed=s.get_editor_world();game=s.get_game_world()
path='/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024.L_CyberpunkBedroom_Pilot20261024'
loaded=u.find_object(None,path)
result=dict(editor_world=ed.get_path_name() if ed else None,game_world=game.get_path_name() if game else None,pilot_loaded=bool(loaded),dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(R/'live-context.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
