"""Read-only snapshot for the reported body grounding/material/weapon regressions."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
if root != Path("D:/FPS3D/FPSGAME").resolve():
    raise RuntimeError("Unexpected project")
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_game_world()

def path(obj):
    return obj.get_path_name() if obj else None

def vector(value):
    return [round(value.x, 3), round(value.y, 3), round(value.z, 3)]

def mesh_state(mesh):
    asset = mesh.get_skeletal_mesh_asset()
    result = {
        "component": mesh.get_name(), "mesh": path(asset),
        "parent": path(mesh.get_attach_parent()), "socket": str(mesh.get_attach_socket_name()),
        "location": vector(mesh.get_world_location()),
        "relative_location": vector(mesh.get_editor_property("relative_location")),
        "scale": vector(mesh.get_world_scale()),
        "visible": mesh.is_visible(), "hidden": mesh.get_editor_property("hidden_in_game"),
        "owner_no_see": mesh.get_editor_property("owner_no_see"),
        "only_owner_see": mesh.get_editor_property("only_owner_see"),
        "animation": path(mesh.get_anim_instance()),
        "overrides": [path(m) for m in mesh.get_editor_property("override_materials")],
        "materials": [path(mesh.get_material(i)) for i in range(mesh.get_num_materials())],
        "slots": [], "bones": {},
    }
    if asset:
        for i, slot in enumerate(asset.get_editor_property("materials")):
            result["slots"].append({"index": i, "name": str(slot.material_slot_name),
                                    "asset_material": path(slot.material_interface),
                                    "shown_lod0": mesh.is_material_section_shown(i, 0)})
        for bone in ("root", "pelvis", "foot_l", "foot_r", "ball_l", "ball_r", "hand_r", "hand_l", "WPN_root", "b_gun"):
            if mesh.does_socket_exist(bone):
                result["bones"][bone] = vector(mesh.get_socket_location(bone))
    return result

report = {"world": path(world), "actors": []}
default_pawn = u.get_default_object(u.FPSGAMECharacter)
report["class_default_mesh_z"] = default_pawn.mesh.get_editor_property("relative_location").z
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.FPSGAMECharacter):
        capsule = actor.get_component_by_class(u.CapsuleComponent)
        item = {"actor": path(actor), "location": vector(actor.get_actor_location()),
                "velocity": vector(actor.get_velocity()),
                "capsule_half_height": capsule.get_scaled_capsule_half_height(),
                "capsule_bottom": actor.get_actor_location().z - capsule.get_scaled_capsule_half_height(),
                "skeletal_meshes": [mesh_state(m) for m in actor.get_components_by_class(u.SkeletalMeshComponent)],
                "static_meshes": []}
        for mesh in actor.get_components_by_class(u.StaticMeshComponent):
            item["static_meshes"].append({"name": mesh.get_name(), "mesh": path(mesh.static_mesh),
                "parent": path(mesh.get_attach_parent()), "location": vector(mesh.get_world_location()),
                "visible": mesh.is_visible(), "hidden": mesh.get_editor_property("hidden_in_game"),
                "only_owner_see": mesh.get_editor_property("only_owner_see"),
                "owner_no_see": mesh.get_editor_property("owner_no_see")})
        report["actors"].append(item)
body_path = json.loads((root / "Content/ColdSteelData/player_body.json").read_text(encoding="utf-8"))["body_mesh"]
body = u.load_asset(body_path)
report["configured_body"] = body_path
report["configured_materials"] = [{"slot": str(s.material_slot_name), "material": path(s.material_interface)} for s in body.get_editor_property("materials")] if body else None
output = root / "Saved/PlayerBodyFix20260921" / ("snapshot-" + datetime.now().strftime("%H%M%S") + ".json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"report": str(output), "world": report["world"], "actor_count": len(report["actors"]),
                  "configured_materials": report["configured_materials"]}))
