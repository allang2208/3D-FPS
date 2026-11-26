"""Geometric audit of the spawn point: which meshes cover it and where the
floor is, using only bounding boxes and the known room extents.

Living room interior (from the Blender build): x 396..1128, y 12..540, floor
z=0, ceiling z=295. Spawn (700,420,100) must be inside that box with clear
headroom and no furniture AABB within the capsule radius.
"""
import json

import unreal

MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_audit2_report.json"

ROOM = {"x0": 396, "x1": 1128, "y0": 12, "y1": 540, "z0": 0, "z1": 295}
Z_START = 100.0
R = 40.0

# furniture-ish meshes whose AABB should not contain the spawn column
FURNITURE = {
    "LIV_furniture", "LIV_micro", "LIV_micro_clutter", "LIV_clutter",
    "LIV_plants", "LIV_rug", "LIV_curtains", "LIV_cables", "DET_practicals",
}

out = {"room": ROOM, "problems": [], "covering": [], "furniture_hits": [],
       "errors": []}

try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(MAP)

    start = None
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.PlayerStart):
            start = a
            break
    if start is None:
        out["errors"].append("no PlayerStart")
        loc = None
    else:
        loc = start.get_actor_location()
        out["player_start"] = [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)]

    if loc is not None:
        # 1. inside the living room footprint?
        if not (ROOM["x0"] + R < loc.x < ROOM["x1"] - R):
            out["problems"].append("x outside room")
        if not (ROOM["y0"] + R < loc.y < ROOM["y1"] - R):
            out["problems"].append("y outside room")
        if not (ROOM["z0"] < loc.z < ROOM["z1"] - 190):
            out["problems"].append("z lacks headroom")

        # 2. what covers this column?
        for a in eas.get_all_level_actors():
            if not isinstance(a, unreal.StaticMeshActor):
                continue
            label = str(a.get_actor_label())
            mesh = a.static_mesh_component.get_editor_property("static_mesh")
            if mesh is None:
                continue
            b = mesh.get_bounding_box()
            if not (b.min.x - R <= loc.x <= b.max.x + R):
                continue
            if not (b.min.y - R <= loc.y <= b.max.y + R):
                continue
            if b.max.z <= 2 or b.min.z >= 180:
                continue
            out["covering"].append(label)
            if label in FURNITURE:
                out["furniture_hits"].append({
                    "label": label,
                    "z": [round(b.min.z, 1), round(b.max.z, 1)],
                    "x": [round(b.min.x, 1), round(b.max.x, 1)],
                    "y": [round(b.min.y, 1), round(b.max.y, 1)],
                })

except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("AUDIT2_WRITTEN")