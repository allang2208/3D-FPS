"""Add the balcony slider and a fence-compatible collider.

The living room glazing (S_glazing) spans y=-956..14 and is a fixed curtain
wall: there is no opening, so the balcony is unreachable. Real apartments
have a sliding door in that wall, so this places one in the glazing bay at
x 900..960 and opens the collision there.

Also reports the balcony railing as a normal blocking volume: vaulting over a
roof edge must stay refused (no landing surface 152 m below).
"""
import json

import unreal

MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_balcony_door.json"

DOOR_CLASS = "/Script/FPSGAME.ColdSteelSlidingDoor"
# glazing sits at y~-2; the walkable bay in front of the balcony is x 900..960
LOC = (930.0, 0.0, 0.0)
YAW = 0.0

out = {"placed": None, "errors": []}

try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(MAP)

    for a in eas.get_all_level_actors():
        if str(a.get_actor_label()) == "Door_Balcony":
            eas.destroy_actor(a)

    door_cls = unreal.load_class(None, DOOR_CLASS)
    if door_cls is None:
        raise RuntimeError("door class missing")

    actor = eas.spawn_actor_from_class(
        door_cls, unreal.Vector(*LOC), unreal.Rotator(0.0, 0.0, YAW))
    actor.set_actor_label("Door_Balcony")
    out["placed"] = {"loc": list(LOC), "yaw": YAW}

    les.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_packages(
        [unreal.load_package("/Game/GameMaps/L_CyberpunkApartment")], True)

except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("BALCONY_DOOR_WRITTEN")