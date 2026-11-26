"""Collision without editor-only subsystems.

Commandlet mode has no StaticMeshEditorSubsystem (it is a UI subsystem), so
build collision from the commandlet-safe path:
  * mark the architecture meshes CTF_USE_COMPLEX_AS_SIMPLE so the render mesh
    itself is used for traces (the apartment shell is already low-poly);
  * on the placed actors set collision enabled, and block all channels.
"""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_collision_report.json"

COLLIDE = {
    "S_plate", "S_walls", "S_floors", "S_ceiling", "S_joinery", "S_finish",
    "S_doors", "S_facade", "S_balcony", "S_glazing", "S_balcony_glass",
    "FOY_room", "COR_room", "KIT_run", "KIT_dining", "B2_room", "B3_room",
    "MST_room", "BA1_room", "BA2_room", "UTL_room", "LIV_furniture",
    "LIV_rug", "DET_practicals", "S_trim",
}

out = {"complex_as_simple": [], "actors_touched": 0, "errors": [], "map": MAP}
eal = unreal.EditorAssetLibrary

# ---- 1. mesh-level trace flag ------------------------------------------
for name in sorted(COLLIDE):
    path = "%s/StaticMeshes/%s.%s" % (BASE, name, name)
    try:
        if not eal.does_asset_exist(path):
            continue
        mesh = eal.load_asset(path)
        mesh.set_editor_property(
            "collision_trace_flag",
            unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_loaded_asset(mesh)
        out["complex_as_simple"].append(name)
    except Exception as exc:  # noqa: BLE001
        out["errors"].append("%s: %s: %s" % (name, type(exc).__name__, exc))

# ---- 2. actor-level collision + block-all -------------------------------
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if les is None or eas is None:
        raise RuntimeError("level/actor subsystem unavailable")
    les.load_level(MAP)
    for a in eas.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        label = a.get_actor_label()
        if label not in COLLIDE:
            continue
        comp = a.static_mesh_component
        comp.set_collision_profile_name(unreal.Name("BlockAll"))
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        comp.set_editor_property("generate_overlap_events", False)
        out["actors_touched"] += 1
    les.save_current_level()
except Exception as exc:  # noqa: BLE001
    out["errors"].append("actors: %s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("COLLISION_REPORT_WRITTEN")