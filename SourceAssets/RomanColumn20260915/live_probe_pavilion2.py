"""Live editor probe, take 2 — read-only.

Fixes from take 1: sweeps only at heights whose 42-radius sphere clears the ground (z=96 and
z=150 cover a standing capsule's middle and top; z=60 covers the legs down to 18 cm), hit
details read through the generic property API because attribute access returns nothing in this
channel, and a control sweep over open ground that MUST come back clear.
"""

import math

import unreal

ORIGIN = (1350.0, -400.0)
R_CAP = 42.0
N_COL = 10


def log(m):
    print("[live2] " + m)


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def describe(hit):
    if not hit:
        return "clear"
    actor = prop(hit, "hit_actor") or prop(hit, "actor")
    comp = prop(hit, "hit_component") or prop(hit, "component")
    loc = prop(hit, "location") or prop(hit, "impact_point")
    name = "?"
    if actor is not None:
        try:
            name = actor.get_actor_label()
        except Exception:
            name = "actor"
    where = ""
    if loc is not None:
        where = " @(%.0f,%.0f,%.0f)" % (loc.x, loc.y, loc.z)
    return "%s%s" % (name, where)


def sphere(start, end, r=R_CAP):
    return unreal.SystemLibrary.sphere_trace_single(
        world, unreal.Vector(*start), unreal.Vector(*end), r,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, False)


def line(start, end):
    return unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(*start), unreal.Vector(*end),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, False)


log("control A: sweep over open ground (must be clear)")
log("  %s" % describe(sphere((3000.0, 3000.0, 96.0), (2200.0, 3000.0, 96.0))))
log("control B: sweep straight through a column (must hit)")
h = sphere((ORIGIN[0] + 700.0, ORIGIN[1], 96.0), (ORIGIN[0] - 100.0, ORIGIN[1], 96.0))
log("  %s" % describe(h))

log("=== height profile at the pavilion (line traces) ===")
for r in (0.0, 200.0, 440.0, 470.0, 500.0, 620.0):
    log("  down r=%4.0f: %s" % (r, describe(line((ORIGIN[0] + r, ORIGIN[1], 1200.0),
                                                  (ORIGIN[0] + r, ORIGIN[1], -200.0)))))

log("=== bay sweeps: 10 bays x 5 heights (capsule 42, ground-clearing heights only) ===")
gap = 360.0 / N_COL
passable = 0
for k in range(N_COL):
    ang = math.radians(gap * (k + 0.5))
    blocked = []
    for z in (60.0, 96.0, 130.0, 150.0, 175.0):
        h = sphere((ORIGIN[0] + 700.0 * math.cos(ang), ORIGIN[1] + 700.0 * math.sin(ang), z),
                   (ORIGIN[0] - 100.0 * math.cos(ang), ORIGIN[1] - 100.0 * math.sin(ang), z))
        if h:
            blocked.append("z=%.0f %s" % (z, describe(h)))
    log("bay %2d: %s" % (k + 1, "; ".join(blocked) if blocked else "PASSABLE"))
    passable += 0 if blocked else 1
log("passable bays: %d/%d" % (passable, N_COL))

log("=== radial walk out from the centre at capsule height ===")
for z in (60.0, 96.0):
    for i in range(8):
        ang = 2.0 * math.pi * i / 8.0
        h = sphere((ORIGIN[0], ORIGIN[1], z),
                   (ORIGIN[0] + 900.0 * math.cos(ang), ORIGIN[1] + 900.0 * math.sin(ang), z))
        log("  z=%.0f dir %3.0f: %s" % (z, math.degrees(ang), describe(h)))
log("RESULT: DONE")
