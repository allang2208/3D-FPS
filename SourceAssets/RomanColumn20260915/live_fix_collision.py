"""Repair the pavilion collision from inside the running editor.

The live overlap probe proved the blocker: RomanPavilion2_Dome's collision overlaps the whole
pavilion interior (z=20 / 96 / 200 / 300 / 500 all report it), while its mesh sits at 360..760.
Its stored collision (ConvexHulls) came out as 3 boxes + 8 hulls + 1 capsule, one of which
reaches the floor and plugs every bay.

Fix: regenerate the collision of the arch, dome and colonnade with AlignedBoxes (one
axis-aligned box per connected shell — the base already proves this fits tightly: its collision
only answers at z=20). Saves through the editor's own package path, which the project trusts.
"""

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
TARGETS = ("SM_RomanPavilionArch_20", "SM_RomanPavilionDome_20", "SM_RomanPavilionColonnade_20")


def log(m):
    print("[fix] " + m)


def collision_summary(path):
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    setup = mesh.get_editor_property("body_setup") if mesh else None
    if not setup:
        return None
    agg = None
    for prop in ("agg_geom", "aggregate_geometry"):
        try:
            agg = setup.get_editor_property(prop)
        except Exception:
            continue
        if agg:
            break
    counts = {}
    if agg:
        for elem in ("box_elems", "convex_elems", "sphere_elems", "sphyl_elems", "taper_elems"):
            try:
                arr = agg.get_editor_property(elem)
                if arr:
                    counts[elem.replace("_elems", "")] = len(arr)
            except Exception:
                pass
    return counts


log("=== before ===")
for name in TARGETS:
    log("%-32s %s" % (name, collision_summary(D + "/" + name)))

log("=== regenerating as one box per shell ===")
for name in TARGETS:
    path = D + "/" + name
    result = SV.generate_collision(path, "AlignedBoxes", 1, 25, False)
    log("%-32s generate success=%s" % (name, getattr(result, "success", result)))

packages = [unreal.load_package(D + "/" + name) for name in TARGETS]
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages(packages, False))

log("=== after ===")
for name in TARGETS:
    log("%-32s %s" % (name, collision_summary(D + "/" + name)))

log("=== re-check the interior with the overlap probe (must be free of the dome) ===")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ORIGIN = (1350.0, -400.0)
for name, (x, y, z) in (("centre z=20", (ORIGIN[0], ORIGIN[1], 20.0)),
                        ("centre z=96", (ORIGIN[0], ORIGIN[1], 96.0)),
                        ("centre z=200", (ORIGIN[0], ORIGIN[1], 200.0)),
                        ("centre z=300", (ORIGIN[0], ORIGIN[1], 300.0)),
                        ("centre z=500", (ORIGIN[0], ORIGIN[1], 500.0)),
                        ("bay1 mouth r=360 z=96", (ORIGIN[0] + 360.0, ORIGIN[1], 96.0)),
                        ("bay1 gap r=520 z=96", (ORIGIN[0] + 520.0, ORIGIN[1], 96.0))):
    hits = unreal.SystemLibrary.sphere_overlap_actors(
        world, unreal.Vector(x, y, z), 42.0,
        [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2],
        unreal.Actor, [])
    log("%-24s -> %s" % (name, [a.get_actor_label() for a in (hits or []) if a] or "nothing"))

log("=== bay sweeps, capsule radius 42 (a hit here would still mean blocked) ===")
import math
gap = 360.0 / 10
passable = 0
for k in range(10):
    ang = math.radians(gap * (k + 0.5))
    blocked = []
    for z in (60.0, 96.0, 150.0):
        h = unreal.SystemLibrary.sphere_trace_single(
            world,
            unreal.Vector(ORIGIN[0] + 700.0 * math.cos(ang), ORIGIN[1] + 700.0 * math.sin(ang), z),
            unreal.Vector(ORIGIN[0] - 100.0 * math.cos(ang), ORIGIN[1] - 100.0 * math.sin(ang), z), 42.0,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, False)
        if h:
            blocked.append("z=%.0f" % z)
    log("bay %2d: %s" % (k + 1, ",".join(blocked) if blocked else "PASSABLE"))
    passable += 0 if blocked else 1
log("passable: %d/10" % passable)
log("RESULT: DONE")
