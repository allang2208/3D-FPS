"""Rebuild the level's pavilion in-process (same assets, same transforms) and sweep it.

Headless traces only answer for actors registered in this process — the level's own actors
loaded from the .umap are NOT queryable (the ground itself returns no hit). Spawning fresh
actors makes the queries real, so this is the trustworthy version of the level test.
Also isolates the columns: their collision is the one asset the build-world test never covered.
"""

import math

import unreal

D = "/Game/Props/RomanColumn20260915"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)
R_COL = 360.0
N_COL = 10
R_CAP = 42.0
Z_ARCH = 280.0
Z_DOME = 360.0
TEST_ORIGIN = (6000.0, 6000.0)      # empty ground far from anything

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def log(m):
    print("[spawn] " + m)


def spawn(mesh_path, x, y, z, label):
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    a = actor_sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z),
                                         unreal.Rotator(0.0, 0.0, 0.0))
    if not a:
        log("spawn FAILED %s" % label)
        return None
    a.set_actor_label(label)
    smc = a.static_mesh_component
    if smc.mobility != unreal.ComponentMobility.MOVABLE:
        smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(mesh)
    return a


def sphere(start, end, radius=R_CAP):
    return unreal.SystemLibrary.sphere_trace_single(
        world, unreal.Vector(*start), unreal.Vector(*end), radius,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def describe(hit, ox, oy):
    if not hit:
        return "clear"
    label = "?"
    try:
        label = hit.hit_actor.get_actor_label() if hit.hit_actor else "?"
    except AttributeError:
        pass
    r = None
    for attr in ("location", "impact_point"):
        try:
            v = getattr(hit, attr)
            r = math.hypot(v.x - ox, v.y - oy)
            break
        except AttributeError:
            continue
    return "%s at r=%.0f" % (label, r if r is not None else -1)


# ---------------------------------------------------------------- sanity: do spawned actors answer?
# The level's own geometry (loaded from the .umap) never answers in a commandlet, but actors
# created in this process do — so the sanity check must use a freshly spawned box.
probe = spawn(D + "/SM_RomanPavilionBase_20", TEST_ORIGIN[0] + 4000.0, TEST_ORIGIN[1] + 4000.0, 0.0, "ProbeSanity")
hit = unreal.SystemLibrary.line_trace_single(
    world, unreal.Vector(TEST_ORIGIN[0] + 4000.0, TEST_ORIGIN[1] + 4000.0, 400.0),
    unreal.Vector(TEST_ORIGIN[0] + 4000.0, TEST_ORIGIN[1] + 4000.0, -100.0),
    unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
log("sanity: freshly spawned actor answers down-trace = %s" % ("HIT z=%.1f" % hit.location.z if hit else "NO HIT"))
if not hit:
    log("RESULT: ABORT - physics queries unavailable in this process")
    raise SystemExit(0)
if probe:
    actor_sub.destroy_actor(probe)

# ---------------------------------------------------------------- isolate the columns
log("=== columns only: 10 columns on r360 at the test site ===")
for k in range(N_COL):
    ang = 2.0 * math.pi * k / N_COL
    spawn(D + "/SM_RomanColumn_Detailed", TEST_ORIGIN[0] + R_COL * math.cos(ang),
          TEST_ORIGIN[1] + R_COL * math.sin(ang), 0.0, "ProbeCol_%02d" % (k + 1))
gap = 360.0 / N_COL
ok = 0
for k in range(N_COL):
    ang = math.radians(gap * (k + 0.5))
    rows = []
    blocked = None
    for z in (30.0, 60.0, 96.0, 130.0, 170.0):
        start = (TEST_ORIGIN[0] + 700.0 * math.cos(ang), TEST_ORIGIN[1] + 700.0 * math.sin(ang), z)
        end = (TEST_ORIGIN[0] - 120.0 * math.cos(ang), TEST_ORIGIN[1] - 120.0 * math.sin(ang), z)
        h = sphere(start, end)
        rows.append("z%.0f=%s" % (z, describe(h, TEST_ORIGIN[0], TEST_ORIGIN[1]) if h else "ok"))
        if h and not blocked:
            blocked = (z, describe(h, TEST_ORIGIN[0], TEST_ORIGIN[1]))
    if blocked:
        log("bay %2d: BLOCKED at z=%.0f by %s   [%s]" % (k + 1, blocked[0], blocked[1], " ".join(rows)))
    else:
        ok += 1
log("columns-only bays passable: %d/%d" % (ok, N_COL))

# straight through a column axis: how wide is the cross-section really?
log("=== cross-section at capsule height through the bay, fine angular scan ===")
for off in range(-18, 19, 3):
    a = math.radians(gap * 0.5 + off)
    start = (TEST_ORIGIN[0] + 700.0 * math.cos(a), TEST_ORIGIN[1] + 700.0 * math.sin(a), 96.0)
    end = (TEST_ORIGIN[0] - 120.0 * math.cos(a), TEST_ORIGIN[1] - 120.0 * math.sin(a), 96.0)
    h = sphere(start, end)
    log("offset %+3d deg: %s" % (off, describe(h, TEST_ORIGIN[0], TEST_ORIGIN[1]) if h else "passable"))

# ---------------------------------------------------------------- whole pavilion
log("=== full pavilion at the test site (same stacking as the level) ===")
spawn(D + "/SM_RomanPavilionBase_20", TEST_ORIGIN[0], TEST_ORIGIN[1], 0.0, "ProbeBase")
spawn(D + "/SM_RomanPavilionArch_20", TEST_ORIGIN[0], TEST_ORIGIN[1], Z_ARCH, "ProbeArch")
spawn(D + "/SM_RomanPavilionDome_20", TEST_ORIGIN[0], TEST_ORIGIN[1], Z_DOME, "ProbeDome")
ok = 0
for k in range(N_COL):
    ang = math.radians(gap * (k + 0.5))
    blocked = None
    for z in (30.0, 60.0, 96.0, 130.0, 170.0):
        h = sphere((TEST_ORIGIN[0] + 700.0 * math.cos(ang), TEST_ORIGIN[1] + 700.0 * math.sin(ang), z),
                   (TEST_ORIGIN[0] - 120.0 * math.cos(ang), TEST_ORIGIN[1] - 120.0 * math.sin(ang), z))
        if h and not blocked:
            blocked = (z, describe(h, TEST_ORIGIN[0], TEST_ORIGIN[1]))
    if blocked:
        log("bay %2d: BLOCKED at z=%.0f by %s" % (k + 1, blocked[0], blocked[1]))
    else:
        ok += 1
log("full pavilion bays passable: %d/%d" % (ok, N_COL))

log("=== inside the pavilion: headroom ===")
for z in (10.0, 96.0, 180.0, 220.0, 300.0):
    h = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(TEST_ORIGIN[0], TEST_ORIGIN[1], z),
        unreal.Vector(TEST_ORIGIN[0], TEST_ORIGIN[1], z + 900.0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
    log("up from z=%.0f: %s" % (z, describe(h, TEST_ORIGIN[0], TEST_ORIGIN[1]) if h else "nothing above"))
log("RESULT: DONE")
