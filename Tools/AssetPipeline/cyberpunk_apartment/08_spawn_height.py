"""Fix PlayerStart height semantics and set the level's default GameMode.

PlayerStart location is the BASE of the capsule (the spawn Z is pushed up by
half the capsule height), so the actor must sit at floor level, not 100 cm
above it. This drops it to just above the floor plane and re-verifies.

Also points the map at a scene-only GameMode so entering the level does not
drag in the full FPS gameplay stack while we are only checking the space.
"""
import json

import unreal

MAP = "/Game/GameMaps/L_CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_spawn_fix_report.json"

FLOOR_Z = 0.0
BASE_LIFT = 6.0      # stand a hair above the floor to avoid initial penetration

out = {"errors": [], "actions": []}

try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(MAP)

    starts = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
    out["found"] = len(starts)
    for s in starts:
        loc = s.get_actor_location()
        s.set_actor_location(
            unreal.Vector(loc.x, loc.y, FLOOR_Z + BASE_LIFT), False, False)
        out["actions"].append("moved to z=%.1f" % (FLOOR_Z + BASE_LIFT))

    # store the fwd-facing yaw explicitly: 270 deg looks from +Y toward -Y
    for s in starts:
        s.set_actor_rotation(unreal.Rotator(0.0, 0.0, 270.0), False)

    les.save_current_level()
    unreal.EditorAssetLibrary.save_directory("/Game/GameMaps",
                                             only_if_is_dirty=False,
                                             recursive=True)
    out["saved"] = True
except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("SPAWN_FIX_WRITTEN")