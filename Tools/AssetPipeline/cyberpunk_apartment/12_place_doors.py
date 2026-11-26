"""Place interactive sliding doors in every doorway of the apartment.

Reuses AColdSteelSlidingDoor (E-key interaction, server-authoritative,
6 s auto-close, slide-blocked rejection) rather than inventing a new door.
The class builds its own frame + two leaves (94.74 x 226.42 cm at scale 1);
the doorway is 240 cm tall, so doors are placed at floor level and rotated
so the slide axis runs along the wall.
"""
import json

import unreal

MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_doors_placed.json"

DOOR_CLASS = "/Script/FPSGAME.ColdSteelSlidingDoor"

# (label, location, yaw)  yaw: 0 => slide axis along Y, 90 => along X
DOORS = [
    ("Door_Master",   (197.0, 546.0, 0.0),   0.0),
    ("Door_Bed2",     (1134.0, 455.0, 0.0),  90.0),
    ("Door_Bed3",     (1134.0, 803.0, 0.0),  90.0),
    ("Door_Bath1",    (370.0, 814.0, 0.0),   0.0),
    ("Door_Bath2",    (162.0, 814.0, 0.0),   0.0),
]

out = {"placed": [], "failed": [], "errors": []}

try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(MAP)

    # clear previous door actors so reruns do not stack
    for a in eas.get_all_level_actors():
        if str(a.get_actor_label()).startswith("Door_"):
            eas.destroy_actor(a)

    door_cls = unreal.load_object(None, DOOR_CLASS)
    if door_cls is None:
        door_cls = unreal.load_class(None, DOOR_CLASS)
    if door_cls is None:
        raise RuntimeError("ColdSteelSlidingDoor class not found")

    for (label, loc, yaw) in DOORS:
        try:
            actor = eas.spawn_actor_from_class(
                door_cls, unreal.Vector(*loc), unreal.Rotator(0.0, 0.0, yaw))
            if actor is None:
                out["failed"].append(label + " (spawn returned None)")
                continue
            actor.set_actor_label(label)
            out["placed"].append({"label": label, "loc": list(loc), "yaw": yaw})
        except Exception as exc:  # noqa: BLE001
            out["failed"].append("%s: %s: %s" % (label, type(exc).__name__, exc))

    les.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_packages(
        [unreal.load_package("/Game/GameMaps/L_CyberpunkApartment")], True)

except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("DOORS_PLACED_WRITTEN")