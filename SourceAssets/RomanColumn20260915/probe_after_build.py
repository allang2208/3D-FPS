"""Read-only: after the full build + editor restart - is BronzeTorch registered and are the 6 torches back."""

import unreal

print("[pf] class = %s" % unreal.load_class(None, "/Script/FPSGAME.BronzeTorch"))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("[pf] world = %s" % (world.get_path_name() if world else None))
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
torches = sorted([a for a in sub.get_all_level_actors() if a.get_actor_label().startswith("ColonnadeTorch_")],
                 key=lambda a: a.get_actor_label())
print("[pf] torches = %d" % len(torches))
for a in torches:
    loc = a.get_actor_location()
    niag = a.get_component_by_class(unreal.NiagaraComponent)
    light = a.get_component_by_class(unreal.PointLightComponent)
    body = a.get_component_by_class(unreal.StaticMeshComponent)
    mesh = body.get_editor_property("static_mesh") if body else None
    asset = niag.get_editor_property("asset") if niag else None
    print("[pf]   %-18s %-12s (%.0f,%.0f,%.0f) mesh=%s flame=%s ignore=%s" % (
        a.get_actor_label(), a.get_class().get_name(), loc.x, loc.y, loc.z,
        mesh.get_name() if mesh else None, asset.get_name() if asset else None,
        light.get_editor_property("intensity") if light else None))
for prop in ("IgniteHour", "ExtinguishHour", "FlameScale"):
    if torches:
        try:
            print("[pf]   %s = %s" % (prop, torches[0].get_editor_property(prop)))
        except Exception as exc:  # noqa: BLE001
            print("[pf]   %s FAILED %s" % (prop, exc))
print("[pf] DONE")
