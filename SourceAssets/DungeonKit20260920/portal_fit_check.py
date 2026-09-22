"""Read-only: where would portals spawn, and is there ground for them?

Mirrors the placement math in SceneTestPortal.cpp::SpawnPortals for the hub and the
dungeon, then traces down at each portal spot so the answer is evidence, not belief.
No actor is spawned and nothing is saved.
"""
import json
import unreal as u

CASES = {
    'DayNight_Lighting': 4,   # Normandy, Trench, Dungeon, Hills (current map skipped)
    'L_Dungeon_Prototype': 1,  # HOME only
}
SPREAD = 440.0
FORWARD = 350.0

actors_api = u.get_editor_subsystem(u.EditorActorSubsystem)
editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
world_subsystem = u.get_editor_subsystem(u.UnrealEditorSubsystem)
out = {}

for level, count in CASES.items():
    if not editor.load_level('/Game/GameMaps/' + level):
        out[level] = {'error': 'load failed'}
        continue
    world = world_subsystem.get_editor_world()
    starts = [a for a in actors_api.get_all_level_actors() if isinstance(a, u.PlayerStart)]
    if not starts:
        out[level] = {'error': 'no PlayerStart'}
        continue
    start = starts[0]
    loc = start.get_actor_location()
    yaw = start.get_actor_rotation().yaw
    facing = u.Rotator(0.0, 0.0, yaw)
    fwd = facing.get_forward_vector()
    rgt = u.MathLibrary.get_right_vector(facing)
    spots = []
    for i in range(count):
        side = (i - (count - 1) * 0.5) * SPREAD
        p = loc + fwd * FORWARD + rgt * side
        found, hit = u.SystemLibrary.line_trace_single(
            world, u.Vector(p.x, p.y, p.z + 200.0), u.Vector(p.x, p.y, p.z - 1500.0),
            u.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], u.DrawDebugTrace.NONE, True)
        z = None
        if found:
            z = hit.impact_point.z + 5.0
        ahead_found, side_hit = u.SystemLibrary.line_trace_single(
            world, u.Vector(p.x, p.y, (z if z is not None else p.z) + 100.0),
            u.Vector(p.x + fwd.x * 150.0, p.y + fwd.y * 150.0, (z if z is not None else p.z) + 100.0),
            u.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], u.DrawDebugTrace.NONE, True)
        spots.append({
            'index': i,
            'side_cm': round(side, 1),
            'xy': [round(p.x, 1), round(p.y, 1)],
            'ground_z': round(z, 1) if z is not None else None,
            'ground_hit': bool(found),
            'blocked_ahead': bool(ahead_found),
        })
    out[level] = {
        'player_start': [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
        'yaw': round(yaw, 1),
        'portal_count': count,
        'spots': spots,
    }

u.log('PORTAL_FIT ' + json.dumps(out))