"""Read the existing game's inspect assets/state without issuing gameplay input."""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
if project != Path("D:/FPS3D/FPSGAME").resolve():
    raise RuntimeError("Unexpected editor project")

def asset_info(obj):
    if obj is None:
        return None
    result = {"path": obj.get_path_name()}
    if isinstance(obj, unreal.AnimSequence):
        result["length"] = obj.get_play_length()
        result["rate_scale"] = obj.get_editor_property("rate_scale")
    return result

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_game_world()
result = {"game_world": world.get_path_name() if world else None, "players": []}
if world:
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FPSGAMECharacter):
        data = {"actor": actor.get_path_name(), "weapon_state": str(actor.get_weapon_state()),
                "magazine": actor.get_magazine_ammo()}
        for name in ("InspectAnimation", "ActiveActionAnimation", "IdleAnimation"):
            data[name] = asset_info(actor.get_editor_property(name))
        graph = actor.get_editor_property("GunplayAnimation")
        data["graph_action"] = asset_info(graph.get_editor_property("ActionClip")) if graph else None
        result["players"].append(data)

output = project / "Saved/Diagnostics/PistolInspectEarlyEnd20261002/active-inspect.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
