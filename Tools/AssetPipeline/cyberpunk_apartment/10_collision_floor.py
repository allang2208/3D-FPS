"""Guarantee a standable floor using the engine's own cube.

Authoring collision into imported BodySetups from a commandlet proved
unreliable - the edits read back as box_count 0 and traces still missed.
The engine's /Engine/BasicShapes/Cube has known-good box collision, so a
scaled cube gives a floor that cannot fall through.

Placed to cover the apartment footprint (x -30..1630, y -1130..540) with its
top face at z=0, matching the modelled floor.
"""
import json

import unreal

MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_floor_cube.json"

CUBE = "/Engine/BasicShapes/Cube.Cube"
# cube is 100x100x100 centred on its origin
SIZE = (1660.0, 1670.0, 60.0)          # cm
CENTER = (800.0, -295.0, -30.0)        # top face lands at z = 0
SCALE = (SIZE[0] / 100.0, SIZE[1] / 100.0, SIZE[2] / 100.0)

out = {"errors": [], "spawned": None, "trace": None}


def trace_floor(actor, loc):
    begin = unreal.Vector(loc.x, loc.y, loc.z + 100.0)
    end = unreal.Vector(loc.x, loc.y, loc.z - 400.0)
    res = unreal.SystemLibrary.line_trace_single(
        world_context_object=actor.get_world(), start=begin, end=end,
        trace_channel=unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        trace_complex=True, actors_to_ignore=[], draw_debug_type=unreal.DrawDebugTrace.NONE,
        ignore_self=True)
    if res is None:
        return {"hit": False}
    # HitResult fields are protected in python; hit/no-hit is what matters here
    return {"hit": True, "result": str(res)[:160]}


try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(MAP)

    # remove any previous attempt so reruns stay clean
    for a in eas.get_all_level_actors():
        if str(a.get_actor_label()).startswith("CollisionFloor"):
            eas.destroy_actor(a)

    mesh = unreal.EditorAssetLibrary.load_asset(CUBE)
    if mesh is None:
        raise RuntimeError("engine cube not found")

    floor = eas.spawn_actor_from_class(unreal.StaticMeshActor,
                                       unreal.Vector(*CENTER),
                                       unreal.Rotator(0, 0, 0))
    floor.set_actor_label("CollisionFloor")
    smc = floor.static_mesh_component
    smc.set_editor_property("static_mesh", mesh)
    smc.set_mobility(unreal.ComponentMobility.STATIC)
    floor.set_actor_scale3d(unreal.Vector(*SCALE))
    smc.set_collision_profile_name(unreal.Name("BlockAll"))
    smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    # The Visibility trace channel skips components whose render state is
    # hidden, and a hidden component also cannot support the pawn. Keep the
    # slab fully visible; it sits under the modelled floor so it is never seen.
    smc.set_visibility(True, True)
    smc.set_editor_property("cast_shadow", False)

    out["spawned"] = {"loc": CENTER, "size": SIZE, "scale": SCALE}

    start = next((a for a in eas.get_all_level_actors()
                  if isinstance(a, unreal.PlayerStart)), None)
    if start is None:
        raise RuntimeError("no PlayerStart")
    out["trace"] = trace_floor(start, start.get_actor_location())

    les.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_packages(
        [unreal.load_package("/Game/GameMaps/L_CyberpunkApartment")], True)

except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("FLOOR_CUBE_WRITTEN")