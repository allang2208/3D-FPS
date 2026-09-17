"""Swap the pavilion's 10 columns in the running editor to the round-plate variant, and save
the level through the editor's own save path."""

import unreal

D = "/Game/Props/RomanColumn20260915"
ROUND = D + "/SM_RomanColumn_Round_20"
MAT = D + "/M_RomanStone_V2"


def log(m):
    print("[sw] " + m)


sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
mesh = unreal.EditorAssetLibrary.load_asset(ROUND)
material = unreal.EditorAssetLibrary.load_asset(MAT)
if not mesh:
    log("round column asset not visible to the editor yet (asset registry may need a refresh)")
    raise SystemExit(0)

swapped, skipped = 0, 0
for a in sub.get_all_level_actors():
    label = a.get_actor_label()
    if not label.startswith("RomanPavilion2_Column"):
        continue
    comp = a.static_mesh_component
    old = comp.static_mesh
    old_name = old.get_name() if old else "None"
    comp.set_static_mesh(mesh)
    if material:
        comp.set_material(0, material)
    # the collision of the new asset must be live for the walk-in check below
    try:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception:
        pass
    swapped += 1
    if swapped <= 2:
        log("%-28s %s -> %s (0.0..260 = %.1f)" % (label, old_name, mesh.get_name(),
                                                  comp.bounds.box_extent.z * 2 if hasattr(comp, "bounds") else -1))
log("swapped %d column actors" % swapped)
log("level saved: %s" % level_sub.save_current_level())

# verify: the interior / bays again, now with the round columns
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ORIGIN = (1350.0, -400.0)
for z in (20.0, 96.0, 200.0, 300.0):
    hits = unreal.SystemLibrary.sphere_overlap_actors(
        world, unreal.Vector(ORIGIN[0], ORIGIN[1], z), 42.0,
        [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2],
        unreal.Actor, [])
    log("interior z=%5.0f -> %s" % (z, [a.get_actor_label() for a in (hits or []) if a] or "nothing"))
import math
gap = 360.0 / 10
passable = 0
for k in range(10):
    ang = math.radians(gap * (k + 0.5))
    blocked = []
    for z in (96.0, 130.0, 170.0):
        h = unreal.SystemLibrary.sphere_trace_single(
            world,
            unreal.Vector(ORIGIN[0] + 700.0 * math.cos(ang), ORIGIN[1] + 700.0 * math.sin(ang), z),
            unreal.Vector(ORIGIN[0] - 60.0 * math.cos(ang), ORIGIN[1] - 60.0 * math.sin(ang), z), 42.0,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, False)
        if h:
            blocked.append("z=%.0f" % z)
    passable += 0 if blocked else 1
    if blocked:
        log("bay %2d blocked at %s" % (k + 1, ",".join(blocked)))
log("bays passable: %d/10" % passable)
log("RESULT: DONE")
