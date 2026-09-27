"""Read the already running world's arrow recovery state without starting PIE."""
from pathlib import Path
import json
import unreal as u

out=Path('D:/FPS3D/FPSGAME/Saved/BowArrowRecovery20260927')
out.mkdir(parents=True,exist_ok=True)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_game_world()
report={'game_world':str(world),'arrows':[]}
if world:
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    if pawn:
        root=pawn.get_editor_property('root_component')
        report['player']={'name':pawn.get_name(),'location':str(pawn.get_actor_location()),
                          'root':root.get_name(),'collision':str(root.get_collision_enabled()),
                          'infinite_reserve':pawn.has_infinite_reserve_ammo(),
                          'overlap_events':root.get_editor_property('generate_overlap_events'),
                          'world_dynamic_response':str(root.get_collision_response_to_channel(u.CollisionChannel.ECC_WORLD_DYNAMIC))}
    arrows=u.GameplayStatics.get_all_actors_of_class(world,u.load_class(None,'/Script/FPSGAME.BowArrow'))
    report['arrow_count']=len(arrows)
    if pawn:
        arrows.sort(key=lambda a:(a.get_actor_location()-pawn.get_actor_location()).length())
    for arrow in arrows[:12]:
        row={'name':arrow.get_name(),'location':str(arrow.get_actor_location()),
             'collision':arrow.get_actor_enable_collision(),'components':[]}
        for c in arrow.get_components_by_class(u.PrimitiveComponent):
            if c.get_name() not in ('AutoRecovery','RecoveryShape'):
                continue
            row['components'].append({'name':c.get_name(),'collision':str(c.get_collision_enabled()),
                                      'location':str(c.get_world_location()),
                                      'overlap_events':c.get_editor_property('generate_overlap_events'),
                                      'overlaps':[a.get_name() for a in c.get_overlapping_actors()]})
        report['arrows'].append(row)
(out/'read-state.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
