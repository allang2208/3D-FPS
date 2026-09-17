"""Can the player walk in? Tests BOTH places end to end.

(A) the level's assembled pavilion
(B) a pavilion placed through the build system's own prefab path (as the player builds it)

A player capsule is radius 42 / half-height 96 (FPSGAMECharacter.cpp:133), so the sweep runs at
three sphere heights — 42 (foot), 96 (waist), 150 (chest) — which together cover 0..192.
Any hit is reported with the blocking actor label so the cause is named, not guessed.
"""

import math

import unreal

LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)
R_COL = 360.0
N_COL = 10
R_CAP = 42.0
SWEEP_Z = (42.0, 96.0, 150.0)
KEY = "ColdSteelPlayer|DayNight_Lighting"
# build-world test site, well clear of the player's own structures around cell (30, -30)
BW_CELL = unreal.IntVector(120, 60, 0)

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()


def log(m):
    print("[walk] " + m)


def sweep(start, end, radius=R_CAP):
    return unreal.SystemLibrary.sphere_trace_single(
        world, unreal.Vector(*start), unreal.Vector(*end), radius,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def where(hit):
    if not hit:
        return "clear"
    out = {}
    for attr in ("hit_actor", "hit_component", "location"):
        try:
            out[attr] = getattr(hit, attr)
        except AttributeError:
            out[attr] = None
    label = out["hit_actor"].get_actor_label() if out["hit_actor"] else "?"
    comp = out["hit_component"].get_name() if out["hit_component"] else "?"
    loc = "(%.0f,%.0f,%.0f)" % (out["location"].x, out["location"].y, out["location"].z) if out["location"] else "?"
    return "%s / %s at %s" % (label, comp, loc)


def bays(ox, oy, tag):
    gap = 360.0 / N_COL
    open_bays, blocked = 0, []
    for k in range(N_COL):
        ang = math.radians(gap * (k + 0.5))
        results = []
        for z in SWEEP_Z:
            start = (ox + 620.0 * math.cos(ang), oy + 620.0 * math.sin(ang), z)
            end = (ox - 300.0 * math.cos(ang), oy - 300.0 * math.sin(ang), z)
            results.append(where(sweep(start, end)))
        if all(r == "clear" for r in results):
            open_bays += 1
        else:
            blocked.append((k + 1, results))
    log("%s: %d/%d bays passable" % (tag, open_bays, N_COL))
    for k, results in blocked:
        for z, r in zip(SWEEP_Z, results):
            if r != "clear":
                log("   bay %d at z=%.0f BLOCKED by %s" % (k, z, r))
    return open_bays


log("=== A) level pavilion ===")
log("A bays: %d/%d passable" % (bays(ORIGIN[0], ORIGIN[1], "A"), N_COL))

log("=== B) build-system pavilion ===")
cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")
bw = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
    cls, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0))
if not bw:
    log("cannot spawn VoxelBuildWorld")
else:
    log("build world init=%s" % bw.call_method("DebugInitialize", args=(KEY,)))
    base = unreal.IntVector(BW_CELL.x, BW_CELL.y, BW_CELL.z)
    placed = []
    for pid, cell in (("pavilion_base", base),
                      ("pavilion_colonnade", unreal.IntVector(base.x, base.y, base.z + 1)),
                      ("pavilion_dome", unreal.IntVector(base.x, base.y, base.z + 18))):
        ok = bw.call_method("PlacePrefab", args=(unreal.Name(pid), cell, 0))
        placed.append((pid, ok))
        log("PlacePrefab %-20s at %s -> %s" % (pid, (cell.x, cell.y, cell.z), ok))
    log("prefab count=%s" % bw.call_method("PrefabCount"))
    # the footprint is 48x48 cells; the piece centre sits at cell + 24 cells
    cx = (base.x + 24) * 20.0
    cy = (base.y + 24) * 20.0
    log("B bays: %d/%d passable" % (bays(cx, cy, "B"), N_COL))
    # what is actually at head height inside, and at the bay mouth?
    for z in (10.0, 96.0, 200.0, 300.0):
        hit = sweep((cx + 620.0, cy, z), (cx - 300.0, cy, z))
        log("   B radial +X at z=%.0f: %s" % (z, where(hit)))
    bw.destroy_actor()
log("RESULT: DONE")
