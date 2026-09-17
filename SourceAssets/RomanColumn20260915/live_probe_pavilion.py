"""Run INSIDE the live editor (ue_python_exec channel), where the physics scene is real.

Read-only: traces only, nothing spawned, nothing saved. Reports whether the pavilion's bays are
actually passable for a player capsule and names the blocking actor for any that are not.
"""

import math

import unreal

ORIGIN = (1350.0, -400.0)
R_CAP = 42.0
N_COL = 10


def log(m):
    print("[live] " + m)


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
log("world=%s" % (world.get_name() if world else "None"))
try:
    sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    log("pie=%s" % sub.is_in_play_in_editor())
except Exception as exc:
    log("pie check unavailable: %s" % type(exc).__name__)
try:
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    if pawn:
        p = pawn.get_actor_location()
        log("player pawn at (%.0f, %.0f, %.0f)" % (p.x, p.y, p.z))
    else:
        log("no player pawn in the editor world")
except Exception as exc:
    log("player pawn lookup failed: %s" % type(exc).__name__)


def line(start, end):
    return unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(*start), unreal.Vector(*end),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def sphere(start, end, r=R_CAP):
    return unreal.SystemLibrary.sphere_trace_single(
        world, unreal.Vector(*start), unreal.Vector(*end), r,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def describe(hit):
    if not hit:
        return "clear"
    name = comp = "?"
    try:
        name = hit.hit_actor.get_actor_label() if hit.hit_actor else "?"
    except AttributeError:
        pass
    try:
        comp = hit.hit_component.get_name() if hit.hit_component else "?"
    except AttributeError:
        pass
    z = None
    for attr in ("location", "impact_point"):
        try:
            z = getattr(hit, attr).z
            break
        except AttributeError:
            continue
    return "%s/%s @ z=%s" % (name, comp, "%.1f" % z if z is not None else "?")


log("=== control + height profile at the pavilion ===")
for r in (0.0, 200.0, 450.0, 470.0, 490.0, 600.0):
    log("down r=%4.0f: %s" % (r, describe(line((ORIGIN[0] + r, ORIGIN[1], 1200.0),
                                             (ORIGIN[0] + r, ORIGIN[1], -200.0)))))

log("=== bay sweeps (capsule r=42) ===")
gap = 360.0 / N_COL
passable = 0
for k in range(N_COL):
    ang = math.radians(gap * (k + 0.5))
    blocked = None
    for z in (30.0, 60.0, 96.0, 130.0, 170.0):
        h = sphere((ORIGIN[0] + 700.0 * math.cos(ang), ORIGIN[1] + 700.0 * math.sin(ang), z),
                   (ORIGIN[0] - 100.0 * math.cos(ang), ORIGIN[1] - 100.0 * math.sin(ang), z))
        if h:
            at = None
            try:
                v = h.location
                at = math.hypot(v.x - ORIGIN[0], v.y - ORIGIN[1])
            except AttributeError:
                pass
            blocked = "z=%.0f %s (r=%.0f)" % (z, describe(h), at if at is not None else -1)
            break
    log("bay %2d: %s" % (k + 1, blocked or "PASSABLE"))
    passable += 0 if blocked else 1
log("passable bays: %d/%d" % (passable, N_COL))

log("=== centre outward, 12 directions (blocker radius) ===")
for i in range(12):
    ang = 2.0 * math.pi * i / 12.0
    h = sphere((ORIGIN[0], ORIGIN[1], 96.0),
               (ORIGIN[0] + 900.0 * math.cos(ang), ORIGIN[1] + 900.0 * math.sin(ang), 96.0))
    if h:
        try:
            v = h.location
            log("dir %3.0f: %s at r=%.0f" % (math.degrees(ang), describe(h),
                                             math.hypot(v.x - ORIGIN[0], v.y - ORIGIN[1])))
        except AttributeError:
            log("dir %3.0f: %s" % (math.degrees(ang), describe(h)))
    else:
        log("dir %3.0f: open to 900" % math.degrees(ang))

log("=== ground height around the pavilion (world z) ===")
for (x, y) in ((1350.0, -400.0), (1350.0, 0.0), (1350.0, -900.0), (900.0, -400.0), (1800.0, -400.0)):
    log("  (%.0f,%.0f): %s" % (x, y, describe(line((x, y, 1200.0), (x, y, -300.0)))))
log("RESULT: DONE")
