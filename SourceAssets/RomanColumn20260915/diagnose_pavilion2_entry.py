"""Why can't the player walk in between two columns? Scans the bays properly.

The earlier check was a single ray at z=150, which only proves that one height is clear.
A player capsule is radius 42 / half-height 96 (FPSGAMECharacter.cpp:133), so this sweeps a
42 sphere along the walking path at capsule centre height and casts rays at every height the
capsule occupies, reporting the blocking component by name.
"""

import math

import unreal

LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)
R_COL = 360.0
N_COL = 10
CAPSULE_R = 42.0
CAPSULE_Z = 96.0        # capsule centre when standing

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()


def log(m):
    print("[in] " + m)


def trace(start, end, radius=0.0):
    if radius > 0.0:
        return unreal.SystemLibrary.sphere_trace_single(
            world, unreal.Vector(*start), unreal.Vector(*end), radius,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
    return unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(*start), unreal.Vector(*end),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def where(hit):
    if not hit:
        return "clear"
    comp = "?"
    try:
        comp = hit.hit_component.get_name() if hit.hit_component else "?"
    except AttributeError:
        pass
    actor = "?"
    try:
        actor = hit.hit_actor.get_actor_label() if hit.hit_actor else "?"
    except AttributeError:
        pass
    loc = "?"
    for attr in ("location", "impact_point"):
        try:
            v = getattr(hit, attr)
            loc = "(%.0f,%.0f,%.0f)" % (v.x, v.y, v.z)
            break
        except AttributeError:
            continue
    return "%s / actor=%s at %s" % (comp, actor, loc)


# --- 1. which bays are open? sweep a capsule-radius sphere from outside to the centre
gap = 360.0 / N_COL
log("=== capsule sweep (r=42, centre z=96) from outside to centre, per bay ===")
blocked_bays = []
for k in range(N_COL):
    ang = math.radians(gap * (k + 0.5))
    start = (ORIGIN[0] + 620.0 * math.cos(ang), ORIGIN[1] + 620.0 * math.sin(ang), CAPSULE_Z)
    end = (ORIGIN[0] - 300.0 * math.cos(ang), ORIGIN[1] - 300.0 * math.sin(ang), CAPSULE_Z)
    hit = trace(start, end, CAPSULE_R)
    if hit:
        blocked_bays.append(k)
    log("bay %2d (%.0f deg): %s" % (k + 1, math.degrees(ang), where(hit)))

# --- 2. height profile through bay 1 (the flat ground one, angle 18 deg)
log("=== ray height profile through bay at 18 deg ===")
ang = math.radians(gap * 0.5)
for z in (5.0, 15.0, 25.0, 40.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0):
    start = (ORIGIN[0] + 620.0 * math.cos(ang), ORIGIN[1] + 620.0 * math.sin(ang), z)
    end = (ORIGIN[0] - 300.0 * math.cos(ang), ORIGIN[1] - 300.0 * math.sin(ang), z)
    log("z=%5.0f: %s" % (z, where(trace(start, end))))

# --- 3. rays at the column axis and a bit off it, to size the real opening
log("=== how wide is the opening? rays at 18 deg offset by degrees ===")
for off in (-16.0, -12.0, -8.0, -4.0, 0.0, 4.0, 8.0, 12.0, 16.0):
    a = math.radians(gap * 0.5 + off)
    start = (ORIGIN[0] + 620.0 * math.cos(a), ORIGIN[1] + 620.0 * math.sin(a), CAPSULE_Z)
    end = (ORIGIN[0] - 300.0 * math.cos(a), ORIGIN[1] - 300.0 * math.sin(a), CAPSULE_Z)
    log("bay1%+5.0f deg: %s" % (off, where(trace(start, end))))

# --- 4. straight down the pavilion axis from just outside to the centre (walk in and turn)
log("=== capsule sweep from the stylobate edge to the centre along +X ===")
start = (ORIGIN[0] + 500.0, ORIGIN[1] + 0.0, CAPSULE_Z)
end = (ORIGIN[0] + 100.0, ORIGIN[1] + 0.0, CAPSULE_Z)
log("radial 500->100: %s" % where(trace(start, end, CAPSULE_R)))

log("RESULT: DONE")
