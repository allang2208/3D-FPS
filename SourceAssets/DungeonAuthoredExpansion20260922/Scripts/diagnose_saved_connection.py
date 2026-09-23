import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
reloaded=False
if not UE.get_game_world() and not dirty_maps:
    if not ED.load_level('/Game/GameMaps/L_Dungeon_AuthoredExpansion'):raise RuntimeError('Cannot reload expansion')
    reloaded=True
world=UE.get_editor_world()
if not world or 'L_Dungeon_AuthoredExpansion' not in world.get_path_name():raise RuntimeError('Wrong map: '+str(world))
report={'world':world.get_path_name(),'reloaded':reloaded,'preserved_dirty_maps':dirty_maps,'segments':{},'traces':[]}
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    if a.get_actor_label() in ['DGN_B_AV2_EntryEnd','DGN_B_AV2_MainCorridor_Floor']:
        r=a.get_actor_rotation();o,e=a.get_actor_bounds(False)
        report['segments'][a.get_actor_label()]={'rotation':{'pitch':r.pitch,'yaw':r.yaw,'roll':r.roll},'bounds':[[o.x,o.y,o.z],[e.x,e.y,e.z]]}
for name,start,end in [('A_exit',[2400,-1310,192],[2400,-1510,192]),('link',[2400,-1510,192],[2400,-1720,192]),('B_entry',[2400,-1710,192],[2400,-1930,192])]:
    hit=u.SystemLibrary.capsule_trace_single_by_profile(world,u.Vector(*start),u.Vector(*end),42,96,'Pawn',False,[],u.DrawDebugTrace.NONE)
    report['traces'].append({'part':name,'blocked':hit is not None,'result':str(hit) if hit else None})
(ROOT/'Receipts/saved-connection-collision.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
