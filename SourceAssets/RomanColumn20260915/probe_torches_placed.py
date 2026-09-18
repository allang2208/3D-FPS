"""Read-only: 6 torches after the swap - class, transform, component wiring, ignition window."""

import unreal

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
torches = sorted([a for a in sub.get_all_level_actors() if a.get_actor_label().startswith("ColonnadeTorch_")],
                 key=lambda a: a.get_actor_label())
print("[tp] torches=%d" % len(torches))
for a in torches:
    loc = a.get_actor_location()
    rot = a.get_actor_rotation()
    niag = a.get_component_by_class(unreal.NiagaraComponent)
    light = a.get_component_by_class(unreal.PointLightComponent)
    body = a.get_component_by_class(unreal.StaticMeshComponent)
    mesh_name = niag_name = None
    try:
        mesh = body.get_editor_property("static_mesh")
        mesh_name = mesh.get_name() if mesh else None
    except Exception as exc:  # noqa: BLE001
        mesh_name = "?%s" % exc
    try:
        asset = niag.get_editor_property("asset")
        niag_name = asset.get_name() if asset else None
    except Exception as exc:  # noqa: BLE001
        niag_name = "?%s" % exc
    lumens = radius = visible = "?"
    if light:
        lumens = light.get_editor_property("intensity")
        radius = light.get_editor_property("attenuation_radius")
        visible = light.get_editor_property("visible")
    print("[tp] %-18s %-12s loc=(%.0f,%.0f,%.0f) yaw=%.0f mesh=%s flame=%s light=%s lm/r%s vis=%s" % (
        a.get_actor_label(), a.get_class().get_name(), loc.x, loc.y, loc.z, rot.yaw,
        mesh_name, niag_name, lumens, radius, visible))
if torches:
    first = torches[0]
    for prop in ("BodyMaterial", "FlameScale", "IgniteHour", "ExtinguishHour", "IgnitionBlendSeconds",
                 "LightLumens", "LightRadiusCm", "EnableFlame", "EnableLight", "LightCastsShadows"):
        try:
            print("[tp]   %-22s = %s" % (prop, first.get_editor_property(prop)))
        except Exception as exc:  # noqa: BLE001
            print("[tp]   %-22s FAILED %s" % (prop, exc))
print("[tp] DONE")
