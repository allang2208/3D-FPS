"""Full diagnostic: level actors + collision flags, read from saved packages."""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_full_diag.json"

out = {"actors": [], "flags": {}, "playerstart": None, "errors": []}

# ---- 1. collision flags straight from the assets -------------------------
for name in ("S_floors", "S_plate", "S_walls", "S_balcony"):
    try:
        m = unreal.EditorAssetLibrary.load_asset(
            "%s/StaticMeshes/%s.%s" % (BASE, name, name))
        b = m.get_editor_property("body_setup")
        out["flags"][name] = str(b.get_editor_property("collision_trace_flag"))
    except Exception as exc:  # noqa: BLE001
        out["flags"][name] = "ERR " + str(exc)

# ---- 2. every actor in the level ----------------------------------------
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(MAP)

    for a in eas.get_all_level_actors():
        cls = a.get_class().get_name()
        lbl = str(a.get_actor_label())
        loc = a.get_actor_location()
        entry = {"label": lbl, "class": cls,
                 "loc": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)]}
        if isinstance(a, unreal.StaticMeshActor):
            smc = a.static_mesh_component
            m = smc.get_editor_property("static_mesh")
            sc = a.get_actor_scale3d()
            entry["scale"] = [round(sc.x, 2), round(sc.y, 2), round(sc.z, 2)]
            entry["collision"] = str(smc.get_collision_enabled())
            entry["profile"] = str(smc.get_collision_profile_name())
            entry["mobility"] = str(smc.get_editor_property("mobility"))
            entry["mesh"] = m.get_name() if m else None
            if m:
                b = m.get_bounding_box()
                entry["world_z"] = [round(b.min.z * sc.z + loc.z, 1),
                                    round(b.max.z * sc.z + loc.z, 1)]
        if isinstance(a, unreal.PlayerStart):
            r = a.get_actor_rotation()
            out["playerstart"] = {"loc": entry["loc"],
                                  "pitch_yaw_roll": [round(r.pitch, 1),
                                                     round(r.yaw, 1),
                                                     round(r.roll, 1)]}
        out["actors"].append(entry)

except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("FULL_DIAG_WRITTEN")