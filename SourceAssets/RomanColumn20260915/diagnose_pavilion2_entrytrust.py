"""Establish whether headless traces are trustworthy, then re-test the bays.

Suspicion: in a commandlet the newly loaded world's physics scene is not queryable until
something registers into it (the earlier run that DID get hits had spawned a probe actor
first). Step 1 proves it; step 2 only trusts the traces once the ground answers.
"""

import math

import unreal

LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)
R_CAP = 42.0
GROUND_PROBE = (3000.0, 3000.0)      # open ground far from anything


def log(m):
    print("[probe] " + m)


sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def down(x, y, z0=600.0, z1=-50.0, radius=0.0):
    if radius > 0.0:
        return unreal.SystemLibrary.sphere_trace_single(
            world, unreal.Vector(x, y, z0), unreal.Vector(x, y, z1), radius,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
    return unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, z0), unreal.Vector(x, y, z1),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def z_of(hit):
    if not hit:
        return None
    for attr in ("location", "impact_point"):
        try:
            return getattr(hit, attr).z
        except AttributeError:
            continue
    return None


log("step 1a: ground trace before any registration: %s" % ("HIT z=%.1f" % z_of(down(*GROUND_PROBE))
                                                           if down(*GROUND_PROBE) else "NO HIT"))
dummy = actors.spawn_actor_from_class(unreal.StaticMeshActor,
                                      unreal.Vector(GROUND_PROBE[0], GROUND_PROBE[1], 500.0),
                                      unreal.Rotator(0.0, 0.0, 0.0))
log("step 1b: spawned a dummy actor (%s)" % (dummy is not None))
hit = down(*GROUND_PROBE)
log("step 1c: ground trace after registration:   %s" % ("HIT z=%.1f" % z_of(hit) if hit else "NO HIT"))
if dummy:
    actors.destroy_actor(dummy)
hit = down(*GROUND_PROBE)
log("step 1d: after destroying the dummy:          %s" % ("HIT z=%.1f" % z_of(hit) if hit else "NO HIT"))

trustworthy = hit is not None
log("TRACES TRUSTWORTHY: %s" % trustworthy)

if trustworthy:
    log("=== ground around the pavilion (expect z=0 plain, z=20 on the stylobate) ===")
    for r in (0.0, 200.0, 460.0, 500.0, 600.0, 1000.0):
        h = down(ORIGIN[0] + r, ORIGIN[1])
        label = "-"
        if h:
            try:
                label = h.hit_actor.get_actor_label() if h.hit_actor else "-"
            except AttributeError:
                pass
        log("r=%5.0f: %s  (%s)" % (r, ("z=%.1f" % z_of(h)) if h else "no hit", label))

    log("=== bay walk-in, capsule radius 42, every height a standing capsule occupies ===")
    gap = 360.0 / 10
    for k in range(10):
        ang = math.radians(gap * (k + 0.5))
        first = None
        for z in (30.0, 60.0, 96.0, 130.0, 170.0):
            start = (ORIGIN[0] + 700.0 * math.cos(ang), ORIGIN[1] + 700.0 * math.sin(ang), z)
            end = (ORIGIN[0] - 120.0 * math.cos(ang), ORIGIN[1] - 120.0 * math.sin(ang), z)
            h = unreal.SystemLibrary.sphere_trace_single(
                world, unreal.Vector(*start), unreal.Vector(*end), R_CAP,
                unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
            if h:
                label, at = "?", None
                try:
                    label = h.hit_actor.get_actor_label() if h.hit_actor else "?"
                except AttributeError:
                    pass
                for attr in ("location", "impact_point"):
                    try:
                        v = getattr(h, attr)
                        at = math.hypot(v.x - ORIGIN[0], v.y - ORIGIN[1])
                        break
                    except AttributeError:
                        continue
                first = "z=%.0f hit %s at r=%.0f" % (z, label, at if at else -1)
                break
        log("bay %2d: %s" % (k + 1, first or "PASSABLE"))

    log("=== along the radius at capsule height (does the stylobate edge stop a walker?) ===")
    for z in (30.0, 96.0):
        start = (ORIGIN[0] + 700.0, ORIGIN[1], z)
        end = (ORIGIN[0], ORIGIN[1], z)
        h = unreal.SystemLibrary.sphere_trace_single(
            world, unreal.Vector(*start), unreal.Vector(*end), R_CAP,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
        label = "clear"
        if h:
            try:
                label = "%s at z=%.1f r=%.0f" % (h.hit_actor.get_actor_label() if h.hit_actor else "?",
                                                 z_of(h),
                                                 math.hypot(h.location.x - ORIGIN[0], h.location.y - ORIGIN[1]))
            except AttributeError:
                label = "hit"
        log("z=%5.0f: %s" % (z, label))
log("RESULT: DONE")
