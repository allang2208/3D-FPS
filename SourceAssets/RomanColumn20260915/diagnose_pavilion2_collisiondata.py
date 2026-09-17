"""Read the actual simple-collision geometry out of the assets, then re-test the level pavilion.

Route A: BodySetup's shape elements — numbers, no physics scene involved, so this is the only
fully trustworthy readout available in a commandlet.
Route B: force RecreatePhysicsState on the level's pavilion actors (the level's own geometry
normally never answers a query in a commandlet) and re-sweep, with a positive control so a
"clear" result can be told apart from a dead physics scene.
"""

import math

import unreal

D = "/Game/Props/RomanColumn20260915"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)
R_CAP = 42.0


def log(m):
    print("[col] " + m)


# ------------------------------------------------------------------ route A
log("=== A) simple collision stored in the assets ===")
for name in ("SM_RomanPavilionBase_20", "SM_RomanPavilionArch_20",
             "SM_RomanPavilionDome_20", "SM_RomanColumn_Detailed",
             "SM_RomanPavilionColonnade_20"):
    mesh = unreal.EditorAssetLibrary.load_asset(D + "/" + name)
    if not mesh:
        log("%s: LOAD FAILED" % name)
        continue
    setup = None
    try:
        setup = mesh.get_editor_property("body_setup")
    except Exception as exc:
        log("%s: body_setup not exposed (%s)" % (name, type(exc).__name__))
        continue
    if not setup:
        log("%s: NO BodySetup -> no simple collision" % name)
        continue
    for prop in ("agg_geom", "aggregate_geometry"):
        try:
            agg = setup.get_editor_property(prop)
        except Exception:
            continue
        if not agg:
            log("%s: %s is empty" % (name, prop))
            continue
        parts = []
        for elem in ("box_elems", "convex_elems", "sphere_elems", "sphyl_elems", "taper_elems"):
            try:
                arr = agg.get_editor_property(elem)
                if arr:
                    parts.append("%s=%d" % (elem, len(arr)))
                    if elem == "box_elems":
                        for i, e in enumerate(arr[:6]):
                            ext = e.get_editor_property("extent")
                            ctr = e.get_editor_property("center")
                            parts.append(" box%d c=(%.0f,%.0f,%.0f) e=(%.0f,%.0f,%.0f)" % (
                                i, ctr.x, ctr.y, ctr.z, ext.x, ext.y, ext.z))
                    if elem == "convex_elems":
                        for i, e in enumerate(arr[:4]):
                            bx = e.get_editor_property("elem_box")
                            parts.append(" hull%d box min=(%.0f,%.0f,%.0f) max=(%.0f,%.0f,%.0f)" % (
                                i, bx.min.x, bx.min.y, bx.min.z, bx.max.x, bx.max.y, bx.max.z))
            except Exception as exc:
                parts.append("%s unreadable(%s)" % (elem, type(exc).__name__))
        log("%s: %s" % (name, "; ".join(parts) if parts else "no shape arrays readable"))

# ------------------------------------------------------------------ route B
log("=== B) level pavilion with forced physics state ===")
sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()

forced = 0
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    label = a.get_actor_label()
    if not (label.startswith("RomanPavilion2") or label == "Floor"):
        continue
    try:
        comp = a.static_mesh_component
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        comp.recreate_physics_state()
        forced += 1
    except Exception as exc:
        log("force failed on %s: %s" % (label, type(exc).__name__))
log("recreated physics state on %d actors" % forced)


def sweep(start, end, radius=R_CAP):
    return unreal.SystemLibrary.sphere_trace_single(
        world, unreal.Vector(*start), unreal.Vector(*end), radius,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def down(x, y, z0, z1):
    return unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, z0), unreal.Vector(x, y, z1),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def label_of(hit):
    if not hit:
        return "nothing"
    try:
        return hit.hit_actor.get_actor_label() if hit.hit_actor else "?"
    except AttributeError:
        return "?"


log("control 1: down through the pavilion centre (must hit base/arch/dome/floor)")
for z1 in (300.0, 100.0, 5.0, -50.0):
    h = down(ORIGIN[0], ORIGIN[1], 800.0, z1)
    log("  to z=%6.0f: %s" % (z1, "%s @ z=%.1f" % (label_of(h), h.location.z) if h else "NO HIT"))
log("control 2: ground far away at (3000,3000)")
h = down(3000.0, 3000.0, 400.0, -100.0)
log("  %s" % ("%s @ z=%.1f" % (label_of(h), h.location.z) if h else "NO HIT"))

alive = bool(down(3000.0, 3000.0, 400.0, -100.0))
log("physics alive: %s" % alive)

if alive:
    log("=== bay sweeps at the LEVEL pavilion (capsule heights) ===")
    gap = 360.0 / 10
    for k in range(10):
        ang = math.radians(gap * (k + 0.5))
        blocked = None
        for z in (30.0, 60.0, 96.0, 130.0, 170.0):
            h = sweep((ORIGIN[0] + 700.0 * math.cos(ang), ORIGIN[1] + 700.0 * math.sin(ang), z),
                      (ORIGIN[0] - 120.0 * math.cos(ang), ORIGIN[1] - 120.0 * math.sin(ang), z))
            if h:
                r = math.hypot(h.location.x - ORIGIN[0], h.location.y - ORIGIN[1])
                blocked = "z=%.0f %s at r=%.0f z=%.0f" % (z, label_of(h), r, h.location.z)
                break
        log("bay %2d: %s" % (k + 1, blocked or "passable"))
log("RESULT: DONE")
