"""Apply only Slag's changed native defaults after its Live Coding patch loads."""
import json
from pathlib import Path
import unreal

OUT = Path("D:/FPS3D/FPSGAME/SourceAssets/HundredEyedSlagMeshy20260930/AggressionV5")
TUNING = {
    "chase_speed": (280.0, 340.0),
    "melee_range": (210.0, 300.0),
    "ash_radius": (300.0, 450.0),
    "charge_range": (400.0, 600.0),
    "charge_speed": (210.0, 650.0),
}
slag_class = unreal.load_class(None, "/Script/FPSGAME.HundredEyedSlagMonster")
if slag_class is None:
    raise RuntimeError("HundredEyedSlagMonster native class is unavailable")

changes = []

def update_defaults(obj):
    edited = []
    for key, (old, new) in TUNING.items():
        before = float(obj.get_editor_property(key))
        # Keep values that the user has explicitly customized.
        if abs(before - old) < 0.001:
            obj.set_editor_property(key, new)
            edited.append(key)
    changes.append({"object": obj.get_path_name(), "changed_properties": edited})

update_defaults(unreal.get_default_object(slag_class))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is not None:
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, slag_class):
        update_defaults(actor)
        movement = actor.get_character_movement()
        speed = float(movement.get_editor_property("max_walk_speed"))
        if abs(speed - 280.0) < 0.001:
            movement.set_editor_property("max_walk_speed", float(actor.get_editor_property("chase_speed")))
        elif abs(speed - 210.0) < 0.001:
            movement.set_editor_property("max_walk_speed", float(actor.get_editor_property("charge_speed")))
            movement.set_editor_property("max_acceleration", 3200.0)

receipt = {
    "revision": "AggressionV5",
    "live_defaults_applied": True,
    "persistent_asset_changes": False,
    "runtime_tested": False,
    "objects": changes,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "live_defaults_applied.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
unreal.log("SLAG_AGGRESSION_V5_LIVE_DEFAULTS_APPLIED " + str(len(changes)))
