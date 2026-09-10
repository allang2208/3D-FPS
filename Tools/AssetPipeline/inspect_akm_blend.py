import bpy
import json
from pathlib import Path

SOURCE = Path(r"E:\3d\akm-classic-staging\akm-classic-unified.blend")
OUTPUT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\akm_blend_contract.json")

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

def matrix_rows(matrix):
    return [[round(value, 8) for value in row] for row in matrix]

def action_slots(action):
    result = []
    for slot in getattr(action, "slots", []):
        result.append({"identifier": slot.identifier, "target_id_type": slot.target_id_type})
    return result

report = {
    "source": str(SOURCE),
    "fps": bpy.context.scene.render.fps,
    "armatures": [],
    "meshes": [],
    "actions": [],
}

for obj in sorted(bpy.data.objects, key=lambda item: item.name):
    if obj.type == "ARMATURE":
        report["armatures"].append({
            "name": obj.name,
            "parent": obj.parent.name if obj.parent else None,
            "matrix_world": matrix_rows(obj.matrix_world),
            "bones": [
                {
                    "name": bone.name,
                    "parent": bone.parent.name if bone.parent else None,
                    "use_deform": bone.use_deform,
                    "matrix_local": matrix_rows(bone.matrix_local),
                }
                for bone in obj.data.bones
            ],
            "active_action": obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None,
            "nla_tracks": [
                {
                    "name": track.name,
                    "strips": [
                        {
                            "name": strip.name,
                            "action": strip.action.name if strip.action else None,
                            "frame_start": strip.frame_start,
                            "frame_end": strip.frame_end,
                        }
                        for strip in track.strips
                    ],
                }
                for track in (obj.animation_data.nla_tracks if obj.animation_data else [])
            ],
        })
    elif obj.type == "MESH":
        modifiers = [modifier.object.name for modifier in obj.modifiers if modifier.type == "ARMATURE" and modifier.object]
        report["meshes"].append({
            "name": obj.name,
            "parent": obj.parent.name if obj.parent else None,
            "armature_modifiers": modifiers,
            "vertex_groups": [group.name for group in obj.vertex_groups],
            "matrix_world": matrix_rows(obj.matrix_world),
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
        })

for action in sorted(bpy.data.actions, key=lambda item: item.name):
    report["actions"].append({
        "name": action.name,
        "frame_range": list(action.frame_range),
        "slots": action_slots(action),
        "users": action.users,
    })

OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({
    "output": str(OUTPUT),
    "armatures": [(item["name"], len(item["bones"]), item["active_action"]) for item in report["armatures"]],
    "meshes": [(item["name"], item["armature_modifiers"], item["vertices"]) for item in report["meshes"]],
    "actions": [(item["name"], item["frame_range"], item["slots"]) for item in report["actions"]],
}, indent=2))
