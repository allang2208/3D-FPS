"""Read-only ownership and map state needed for scoped integration/retirement."""
import unreal as u,json
from pathlib import Path
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem);ed=s.get_editor_world();game=s.get_game_world()
maps=['/Game/GameMaps/L_CyberpunkApartment','/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024']
loaded={p:bool(u.find_object(None,p+'.'+p.rsplit('/',1)[-1])) for p in maps}
result=dict(editor_world=ed.get_path_name() if ed else None,game_world=game.get_path_name() if game else None,loaded=loaded,dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],dirty_content=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
(R/'context.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
