"""Build a playable level from the imported apartment meshes.

The glTF import gives us 80 static meshes at the origin (each already carries
its own world-space geometry, so they simply need to be instanced at 0,0,0).
Lights are not part of the glTF (glTF has no UE light semantics), so this
script re-creates the key practicals and the night world on the UE side.
"""
import json
import math

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment/StaticMeshes"
MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_level_report.json"

report = {"map": MAP, "placed": 0, "lights": 0, "errors": [], "notes": []}


def log(m):
    report["notes"].append(m)


try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        les.load_level(MAP)
        log("loaded existing level")
    else:
        les.new_level(MAP)
        log("created new level " + MAP)

    # wipe anything already in the map so reruns stay clean
    for a in eas.get_all_level_actors():
        eas.destroy_actor(a)

    # ---- instance every imported mesh at the origin -----------------------
    names = unreal.EditorAssetLibrary.list_assets(BASE, recursive=False, include_folder=False)
    for path in names:
        short = path.split("/")[-1].split(".")[0]
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            continue
        actor = eas.spawn_actor_from_class(unreal.StaticMeshActor,
                                           unreal.Vector(0, 0, 0),
                                           unreal.Rotator(0, 0, 0))
        actor.set_actor_label(short)
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
        actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
        report["placed"] += 1
    log("instanced %d meshes" % report["placed"])

    # ---- lights: the room was designed for a night interior --------------
    def add_light(label, cls, loc, intensity, color, **kw):
        la = eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(0, 0, 0))
        la.set_actor_label(label)
        comp = la.get_component_by_class(unreal.LightComponent)
        comp.set_intensity(intensity)
        comp.set_light_color(color)
        for k, v in kw.items():
            setattr(comp, k, v)
        report["lights"] += 1
        return la

    # living room key + fill (warm, from the ceiling track)
    add_light("L_living_key", unreal.RectLight, (740, 110, 280), 6000,
              unreal.LinearColor(1.0, 0.886, 0.745, 1.0))
    add_light("L_living_fill", unreal.RectLight, (1020, 360, 260), 2600,
              unreal.LinearColor(0.745, 0.824, 1.0, 1.0))
    # corridor strip
    add_light("L_corr", unreal.RectLight, (560, 610, 285), 3200,
              unreal.LinearColor(0.784, 0.902, 1.0, 1.0))
    # kitchen
    add_light("L_kitchen", unreal.RectLight, (672, 910, 230), 3400,
              unreal.LinearColor(1.0, 0.878, 0.729, 1.0))
    # master bedroom
    add_light("L_master", unreal.RectLight, (200, 260, 286), 3000,
              unreal.LinearColor(1.0, 0.886, 0.769, 1.0))
    # bathroom
    add_light("L_bath", unreal.RectLight, (376, 950, 280), 2200,
              unreal.LinearColor(0.922, 0.949, 1.0, 1.0))
    # foyer
    add_light("L_foyer", unreal.RectLight, (1000, 880, 284), 2400,
              unreal.LinearColor(1.0, 0.910, 0.784, 1.0))
    log("added %d rect lights" % report["lights"])

    # ---- night sky: a low-intensity directional fill + fog ---------------
    sun = eas.spawn_actor_from_class(unreal.DirectionalLight,
                                     unreal.Vector(0, 0, 500),
                                     unreal.Rotator(-28, 200, 0))
    sun.set_actor_label("L_city_sky")
    sc = sun.get_component_by_class(unreal.LightComponent)
    sc.set_intensity(0.35)
    sc.set_light_color(unreal.LinearColor(0.471, 0.549, 1.0, 1.0))
    report["lights"] += 1

    # ---- save ------------------------------------------------------------
    unreal.EditorAssetLibrary.save_directory("/Game/GameMaps", only_if_is_dirty=False, recursive=True)
    les.save_current_level()
    log("level saved")

except Exception as exc:  # noqa: BLE001
    report["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2)
unreal.log("LEVEL_REPORT_WRITTEN")