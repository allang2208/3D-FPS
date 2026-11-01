"""Inspect collision in the existing PIE world, without triggering gameplay."""
import unreal as u, json, math
from pathlib import Path

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result = {'game_world': world.get_path_name() if world else None}
if world:
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    if pawn:
        pos = pawn.get_actor_location()
        z = pos.z - pawn.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
        yaw = math.radians(pawn.get_control_rotation().yaw)
        point = u.Vector(pos.x+125*math.cos(yaw), pos.y+125*math.sin(yaw), z)
        def vector(v): return [v.x, v.y, v.z]
        def brief(hit):
            if not hit: return None
            h = hit.to_dict()
            return {'point':vector(h['impact_point']), 'normal':vector(h['impact_normal']), 'overlap':h['initial_overlap'], 'actor':h['hit_actor'].get_path_name() if h['hit_actor'] else None, 'component':h['hit_component'].get_path_name() if h['hit_component'] else None}
        traces = []
        for complex_collision in [False, True]:
            ignored = [pawn]
            def trace(a, b):
                for _ in range(32):
                    hit = u.SystemLibrary.line_trace_single(world, a, b, u.TraceTypeQuery.ECC_VISIBILITY, complex_collision, ignored, u.DrawDebugTrace.NONE)
                    if not hit: return None
                    actor = hit.to_dict()['hit_actor']
                    if actor and (isinstance(actor, u.Pawn) or actor.get_component_by_class(u.MonsterCombatComponent)):
                        ignored.append(actor)
                        continue
                    return hit
                return None
            original = trace(point+u.Vector(0,0,80), point-u.Vector(0,0,65))
            chain = {'complex':complex_collision, 'origin':brief(original), 'strikes':[]}
            if original:
                start = original.to_dict()['impact_point'] + u.Vector(0,0,2)
                ground = start
                for step in range(1,19):
                    candidate = u.Vector(start.x+100*step*math.cos(yaw), start.y+100*step*math.sin(yaw), ground.z)
                    wall = trace(ground+u.Vector(0,0,50), candidate+u.Vector(0,0,50))
                    floor = trace(candidate+u.Vector(0,0,120), candidate-u.Vector(0,0,220))
                    if wall or not floor or floor.to_dict()['impact_normal'].z < .5:
                        chain['stopped']={'step':step,'wall':brief(wall),'floor':brief(floor)}
                        break
                    ground = floor.to_dict()['impact_point']
                    if step%6==0: chain['strikes'].append(vector(ground))
            traces.append(chain)
        result.update(location=vector(pos),yaw=pawn.get_control_rotation().yaw,traces=traces)
Path(__file__).with_name('ground_probe.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
