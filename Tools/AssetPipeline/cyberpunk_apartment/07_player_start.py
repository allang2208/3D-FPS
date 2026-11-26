"""Add a PlayerStart inside the apartment (living room) and verify clearance.

Without a PlayerStart the GameMode spawns the pawn at (0,0,0), which sits
inside the west exterior wall - the player then falls ~152 m to the city
ground. This script places the start in the living room and rejects any
candidate that overlaps furniture, by testing against mesh bounding boxes.
"""
import json

import unreal

MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_spawn_report.json"

# architectural shell: not obstacles for a standing player
SHELL = {
    "S_plate", "S_walls", "S_floors", "S_ceiling", "S_trim", "S_joinery",
    "S_finish", "S_glazing", "S_facade", "S_balcony", "S_balcony_glass",
    "S_doors", "CITY_blocks", "CITY_ground", "CITY_horizon", "CITY_fog",
    "CITY_signs", "CITY_traffic", "CITY_our_tower", "CITY_bridges",
    "DET_ceiling_services", "DET_wires", "DET_facade_out", "DET_floor",
    "DET_graffiti", "DET_wall_greeble",
}

# living room interior: x 396..1128, y 12..540 (cm)
CANDIDATES = [
    (762, 200, 90),    # centre-south of the living room, facing north
    (600, 180, 90),
    (900, 180, 90),
    (520, 300, 90),
    (980, 300, 90),
    (700, 420, 270),
    (762, 460, 270),
    (450, 250, 90),
]

RADIUS = 45.0          # player capsule radius + margin (cm)
Z_LOW, Z_HIGH = 0.0, 176.0   # capsule vertical span above the floor

out = {"map": MAP, "chosen": None, "rejected": [], "errors": [],
       "player_start": None}


def overlaps(bmin, bmax, cx, cy):
    """AABB vs vertical capsule column test."""
    nx = max(bmin.x, min(cx, bmax.x))
    ny = max(bmin.y, min(cy, bmax.y))
    d = ((cx - nx) ** 2 + (cy - ny) ** 2) ** 0.5
    return d < RADIUS


try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if les is None or eas is None:
        raise RuntimeError("subsystems unavailable in this mode")

    les.load_level(MAP)

    # ---- collect obstacle boxes from the placed actors -------------------
    obstacles = []
    for a in eas.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        label = str(a.get_actor_label())
        if label in SHELL:
            continue
        smc = a.static_mesh_component
        mesh = smc.get_editor_property("static_mesh")
        if mesh is None:
            continue
        b = mesh.get_bounding_box()
        # actor transform is identity for the imported set, but apply it anyway
        loc = a.get_actor_location()
        obstacles.append((b.min + loc, b.max + loc, label))

    out["obstacle_count"] = len(obstacles)

    # ---- pick the first clear candidate ---------------------------------
    chosen = None
    for (cx, cy, yaw) in CANDIDATES:
        hits = [lbl for (bmin, bmax, lbl) in obstacles
                if overlaps(bmin, bmax, cx, cy)
                and bmax.z > Z_LOW and bmin.z < Z_HIGH]
        if hits:
            out["rejected"].append({"pos": [cx, cy], "yaw": yaw, "hits": hits[:6]})
            continue
        chosen = (cx, cy, yaw)
        break

    if chosen is None:
        raise RuntimeError("no clear candidate in the living room")

    cx, cy, yaw = chosen

    # ---- replace any existing PlayerStart -------------------------------
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.PlayerStart):
            eas.destroy_actor(a)
    # a lone start is enough; the shell floor carries the player

    ps = eas.spawn_actor_from_class(
        unreal.PlayerStart,
        unreal.Vector(cx, cy, 100.0),
        unreal.Rotator(0.0, 0.0, float(yaw)))
    ps.set_actor_label("PlayerStart_Apartment")
    out["player_start"] = {
        "location": [round(ps.get_actor_location().x, 1),
                     round(ps.get_actor_location().y, 1),
                     round(ps.get_actor_location().z, 1)],
        "yaw": yaw,
    }
    out["chosen"] = [cx, cy, yaw]

    les.save_current_level()
    unreal.EditorAssetLibrary.save_directory("/Game/GameMaps",
                                             only_if_is_dirty=False,
                                             recursive=True)
    out["saved"] = True

except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("SPAWN_REPORT_WRITTEN")