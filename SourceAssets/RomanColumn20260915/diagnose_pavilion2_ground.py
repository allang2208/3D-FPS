"""Measure the ground around the pavilion — the thing I never re-verified after moving it.

Trick for the dead physics scene: initializing a VoxelBuildWorld spawns its chunk meshes into
the world (DebugInitialize), which is enough to make queries answer. A control trace proves it
before any conclusion is drawn. Then: height profile inside/outside the stylobate (the step the
player faces) and bay sweeps at capsule heights.
"""

import math

import unreal

KEY = "ColdSteelPlayer|DayNight_Lighting"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)
OLD_ORIGIN = (1350.0, 0.0)
R_CAP = 42.0

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def log(m):
    print("[gnd] " + m)


cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")
bw = actors.spawn_actor_from_class(cls, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0))
try:
    log("warm-up DebugInitialize=%s (blocks=%s)" % (bw.call_method("DebugInitialize", args=(KEY,)),
                                                    bw.call_method("BlockCount")))
except Exception as exc:
    log("warm-up failed: %s" % exc)


def down(x, y, z0=1200.0, z1=-400.0):
    return unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, z0), unreal.Vector(x, y, z1),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def hit_label(hit):
    if not hit:
        return "NO HIT"
    name = "?"
    try:
        name = hit.hit_actor.get_actor_label() if hit.hit_actor else "?"
    except AttributeError:
        pass
    return "%s @ z=%.1f" % (name, hit.location.z) if hasattr(hit, "location") else name


control = down(3000.0, 3000.0)
log("control (open ground at 3000,3000): %s" % hit_label(control))
alive = control is not None and "NO HIT" not in hit_label(control)
log("physics answering: %s" % alive)
if not alive:
    log("RESULT: ABORT - still no usable queries")
    raise SystemExit(0)

log("=== ground height along the approach to the pavilion (y from +600 to -1500 at x=1350) ===")
for y in range(600, -1501, -100):
    log("  (1350, %5d): %s" % (y, hit_label(down(ORIGIN[0], float(y)))))

log("=== height profile through the pavilion centre (radial, +X direction) ===")
for r in (0.0, 100.0, 200.0, 300.0, 400.0, 450.0, 460.0, 470.0, 480.0, 500.0, 550.0, 700.0, 900.0):
    log("  r=%4.0f: %s" % (r, hit_label(down(ORIGIN[0] + r, ORIGIN[1]))))

log("=== same profile at the OLD pavilion site (the one the player could enter) ===")
for r in (0.0, 400.0, 480.0, 500.0, 700.0):
    log("  old r=%4.0f: %s" % (r, hit_label(down(OLD_ORIGIN[0] + r, OLD_ORIGIN[1]))))

log("=== top surface of the stylobate (expect four points at z=20 inside r460) ===")
for r in (0.0, 200.0, 420.0, 455.0):
    log("  r=%4.0f: %s" % (r, hit_label(down(ORIGIN[0] + r, ORIGIN[1]))))

log("=== bay sweep at capsule heights (1 = the bay on +X) ===")
gap = 360.0 / 10
for k in range(10):
    ang = math.radians(gap * (k + 0.5))
    blocked = None
    for z in (30.0, 60.0, 96.0, 130.0, 170.0):
        h = unreal.SystemLibrary.sphere_trace_single(
            world, unreal.Vector(ORIGIN[0] + 700.0 * math.cos(ang), ORIGIN[1] + 700.0 * math.sin(ang), z),
            unreal.Vector(ORIGIN[0] - 120.0 * math.cos(ang), ORIGIN[1] - 120.0 * math.sin(ang), z), R_CAP,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
        if h:
            blocked = "z=%.0f %s" % (z, hit_label(h))
            break
    log("bay %2d: %s" % (k + 1, blocked or "passable"))
bw.destroy_actor()
log("RESULT: DONE")
