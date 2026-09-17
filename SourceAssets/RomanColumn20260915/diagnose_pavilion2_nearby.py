"""List everything near the pavilion and re-test entry with the player capsule, including the
stylobate's own collision. Answers: what is standing in the way, by actor label."""

import math

import unreal

LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)
R_CAP = 42.0

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def log(m):
    print("[near] " + m)


log("=== actors within 1600 cm of the pavilion centre (%.0f, %.0f) ===" % ORIGIN)
near = []
for a in actors:
    try:
        loc = a.get_actor_location()
    except Exception:
        continue
    d = math.hypot(loc.x - ORIGIN[0], loc.y - ORIGIN[1])
    if d <= 1600.0:
        mesh = "-"
        try:
            m = a.static_mesh_component.static_mesh
            mesh = m.get_name() if m else "(none)"
        except Exception:
            pass
        near.append((d, a.get_actor_label(), mesh, loc))
for d, label, mesh, loc in sorted(near):
    log("%7.1f cm  %-30s %-32s loc=(%.0f,%.0f,%.0f)" % (d, label, mesh, loc.x, loc.y, loc.z))
log("near count: %d (level total %d)" % (len(near), len(actors)))

log("=== stylobate collision: down-probes at increasing radius (expect top z=20 inside r460) ===")
for r in (0.0, 100.0, 200.0, 300.0, 400.0, 460.0, 490.0, 520.0, 600.0):
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(ORIGIN[0] + r, ORIGIN[1], 600.0), unreal.Vector(ORIGIN[0] + r, ORIGIN[1], -50.0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
    z, label, comp = "no hit", "-", "-"
    if hit:
        try:
            z = "%.1f" % hit.location.z
        except AttributeError:
            pass
        try:
            label = hit.hit_actor.get_actor_label() if hit.hit_actor else "-"
        except AttributeError:
            pass
        try:
            comp = hit.hit_component.get_name() if hit.hit_component else "-"
        except AttributeError:
            pass
    log("r=%5.0f  hit z=%-8s %-28s %s" % (r, z, label, comp))

log("=== horizontal probe at z=10 from outside to centre (does the stylobate rim block?) ===")
for z in (5.0, 10.0, 18.0, 24.0):
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(ORIGIN[0] + 620.0, ORIGIN[1], z), unreal.Vector(ORIGIN[0] - 100.0, ORIGIN[1], z),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
    label = "-"
    if hit:
        try:
            label = "%s @ r=%.0f" % (hit.hit_actor.get_actor_label() if hit.hit_actor else "-",
                                     math.hypot(hit.location.x - ORIGIN[0], hit.location.y - ORIGIN[1]))
        except AttributeError:
            label = "hit"
    log("z=%5.0f: %s" % (z, label if hit else "clear"))

log("=== capsule-sized sweep at the bay, three heights (final word) ===")
gap = 360.0 / 10
for k in (0, 4, 8):
    ang = math.radians(gap * (k + 0.5))
    for z in (30.0, 60.0, 96.0, 130.0, 170.0):
        start = (ORIGIN[0] + 700.0 * math.cos(ang), ORIGIN[1] + 700.0 * math.sin(ang), z)
        end = (ORIGIN[0] - 100.0 * math.cos(ang), ORIGIN[1] - 100.0 * math.sin(ang), z)
        hit = unreal.SystemLibrary.sphere_trace_single(
            world, unreal.Vector(*start), unreal.Vector(*end), R_CAP,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
        label = "clear"
        if hit:
            try:
                label = "%s @ %.0f cm from centre" % (
                    hit.hit_actor.get_actor_label() if hit.hit_actor else "-",
                    math.hypot(hit.location.x - ORIGIN[0], hit.location.y - ORIGIN[1]))
            except AttributeError:
                label = "hit"
        log("bay %d z=%5.0f: %s" % (k + 1, z, label))
log("RESULT: DONE")
