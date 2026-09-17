"""Identify the prefabs in the player's build world by their real bounds (no physics needed)."""

import unreal

KEY = "ColdSteelPlayer|DayNight_Lighting"

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level("/Game/GameMaps/DayNight_Lighting")


def log(m):
    print("[idp] " + m)


cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")
bw = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
    cls, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0))
log("init=%s blocks=%s prefabs=%s" % (bw.call_method("DebugInitialize", args=(KEY,)),
                                      bw.call_method("BlockCount"), bw.call_method("PrefabCount")))

for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if not a.actor_has_tag("VoxelBuildPrefab"):
        continue
    mesh_name = "?"
    for prop in ("mesh_component", "prefab_mesh", "static_mesh_component"):
        try:
            m = getattr(a, prop).static_mesh
            if m:
                mesh_name = m.get_name()
                break
        except Exception:
            continue
    loc = a.get_actor_location()
    extent = None
    try:
        extent = a.get_editor_property("root_component").get_editor_property("bounds").box_extent
    except Exception:
        pass
    if extent is None:
        try:
            m = a.mesh_component.static_mesh
            extent = m.get_bounds().box_extent
        except Exception:
            pass
    log("%-30s loc=(%.0f,%.0f,%.0f) mesh=%s size=%s" % (
        a.get_actor_label(), loc.x, loc.y, loc.z, mesh_name,
        "%.0f x %.0f x %.0f" % (extent.x * 2, extent.y * 2, extent.z * 2) if extent else "?"))
bw.destroy_actor()
log("RESULT: DONE")
