"""Reproduce only the reported crouch-to-idle body offset in the active PIE pawn."""
import json
import time
import builtins
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
if root != Path("D:/FPS3D/FPSGAME").resolve():
    raise RuntimeError("Unexpected project")
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world is None:
    raise RuntimeError("PIE is required for this explicit diagnostic")
pawn = u.GameplayStatics.get_player_character(world, 0)
if not isinstance(pawn, u.FPSGAMECharacter):
    raise RuntimeError("Expected FPSGAMECharacter")
mesh = pawn.mesh
capsule = pawn.get_component_by_class(u.CapsuleComponent)
was_crouched = pawn.get_editor_property("is_crouched")
samples = []


def record(stage):
    samples.append({"stage": stage, "crouched": pawn.get_editor_property("is_crouched"),
                    "capsule_half_height": capsule.get_unscaled_capsule_half_height(),
                    "capsule_bottom": capsule.get_world_location().z - capsule.get_scaled_capsule_half_height(),
                    "mesh_relative_z": mesh.get_editor_property("relative_location").z,
                    "mesh_world_z": mesh.get_world_location().z,
                    "ball_l_world_z": mesh.get_socket_location("ball_l").z})


record("initial_crouched" if was_crouched else "initial")
if was_crouched:
    pawn.un_crouch()
else:
    pawn.crouch()
state = {"phase": 1 if was_crouched else 0, "next": time.monotonic() + 0.6, "handle": None}


def tick(delta):
    if time.monotonic() < state["next"]:
        return
    try:
        if state["phase"] == 0:
            record("crouched")
            pawn.un_crouch()
            state["phase"] = 1
            state["next"] = time.monotonic() + 0.6
            return
        record("standing_again")
        destination = root / "Saved/PlayerBodyFix20260921" / ("crouch-" + time.strftime("%H%M%S") + ".json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(samples, indent=2), encoding="utf-8")
        print("PLAYER_BODY_CROUCH " + str(destination) + " " + json.dumps(samples))
    except Exception as error:
        u.log_error(str(error))
    u.unregister_slate_post_tick_callback(state["handle"])
    del builtins._fps_player_body_crouch_tick


builtins._fps_player_body_crouch_tick = tick
state["handle"] = u.register_slate_post_tick_callback(tick)
print("Requested crouch/stand offset probe; result writes after two engine ticks with settling time.")
