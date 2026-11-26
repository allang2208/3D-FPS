"""Spawn in the open floor of the living room.

UE living room: x 396..1128, y -540..-12.
Furniture occupies:
  sofa      x 892..1212  y -356..-254
  coffee    x 738.. 912  y -354..-256
  armchairA x 558.. 652  y -202..-108
  armchairB x 558.. 652  y -492..-398
  TV wall   x 411.. 457  y -440..-150
Open circulation area is x 660..880, y -470..-120, so (770, -300) is clear
of every piece. Yaw 180 faces the sofa / coffee table (-Y is the window side).
"""
import json

import unreal

MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_spawn_final.json"

LOC = (790.0, -180.0, 6.0)
YAW = 180.0

out = {"errors": [], "placed": None}

try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(MAP)

    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.PlayerStart):
            eas.destroy_actor(a)

    ps = eas.spawn_actor_from_class(unreal.PlayerStart,
                                    unreal.Vector(*LOC),
                                    unreal.Rotator(0.0, 0.0, YAW))
    ps.set_actor_label("PlayerStart_Apartment")

    # verify the point is inside the room and clear of the furniture boxes
    boxes = {
        "sofa": ((892, 1212), (-356, -254)),
        "coffee": ((738, 912), (-354, -256)),
        "armchairA": ((558, 652), (-202, -108)),
        "armchairB": ((558, 652), (-492, -398)),
        "tv": ((411, 457), (-440, -150)),
    }
    hits = [k for k, (xr, yr) in boxes.items()
            if xr[0] - 45 < LOC[0] < xr[1] + 45 and yr[0] - 45 < LOC[1] < yr[1] + 45]

    out["placed"] = {
        "loc": list(LOC), "yaw": YAW,
        "inside_room": 396 < LOC[0] < 1128 and -540 < LOC[1] < -12,
        "furniture_overlap": hits,
    }

    les.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_packages(
        [unreal.load_package("/Game/GameMaps/L_CyberpunkApartment")], True)

except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("SPAWN_FINAL_WRITTEN")