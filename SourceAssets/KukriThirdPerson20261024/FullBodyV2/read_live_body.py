"""Read the user's existing game world; never create a world or change its state."""
import json
from pathlib import Path
import unreal as u

out = {"world": None, "players": []}
def path(x):
    return x.get_path_name() if x else None
def prop(x, name):
    try:
        v = x.get_editor_property(name)
        if isinstance(v, u.Object):
            return path(v)
        return str(v)
    except Exception as exc:
        return "unavailable: " + str(exc)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out["world"] = path(world)
if world:
    for p in u.GameplayStatics.get_all_actors_of_class(world, u.FPSGAMECharacter):
        entry = {"pawn": path(p), "local": p.is_locally_controlled(), "meshes": [], "body": []}
        for m in p.get_components_by_class(u.SkeletalMeshComponent):
            a = m.get_anim_instance()
            row = {"component": path(m), "mesh": path(m.get_skeletal_mesh_asset()), "anim": path(a),
                   "anim_class": path(a.get_class()) if a else None}
            for n in ("leader_pose_component", "visible", "hidden_in_game", "owner_no_see", "only_owner_see", "disable_post_process_blueprint"):
                row[n] = prop(m,n)
            if a and isinstance(a, u.FPSPlayerBodyAnimInstance):
                row["clips"] = prop(a,"clips")
            entry["meshes"].append(row)
        for b in p.get_components_by_class(u.FPSPlayerBodyComponent):
            entry["body"].append({"component": path(b), "properties": {n: prop(b,n) for n in ("replicated_state", "replicated_weapons", "replicated_appearance")}})
        out["players"].append(entry)
    for command in ("getall FPSPlayerBodyComponent ReplicatedState", "getall FPSPlayerBodyAnimInstance Clips"):
        u.SystemLibrary.execute_console_command(world,command)
target=Path(__file__).with_name("live-body.json")
target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False))
