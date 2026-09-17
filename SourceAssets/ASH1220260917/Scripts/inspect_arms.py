"""Inspect the accepted arms blend used as the fitting host for new rifles.

Run: blender --background --factory-startup --python-exit-code 1 --python inspect_arms.py
"""
import json
import os

import bpy
from mathutils import Vector

BLEND = r"D:\FPS3D\FPSGAME\SourceAssets\M4TacticalToss20260910\M4_Hand_MAT_Editable.blend"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "Reference"))

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene

report = {"blend": BLEND, "objects": [], "actions": [], "bones": {}, "pose_idle0": {}}


def r3(v):
    return [round(float(c), 6) for c in v]


for obj in scene.objects:
    entry = {"name": obj.name, "type": obj.type, "parent": obj.parent.name if obj.parent else None}
    if obj.type == "MESH":
        me = obj.data
        entry["vertices"] = len(me.vertices)
        entry["materials"] = [m.name if m else None for m in me.materials]
        entry["modifiers"] = [(m.type, m.object.name if getattr(m, "object", None) else None) for m in obj.modifiers]
        lo = [min((obj.matrix_world @ v.co)[i] for v in me.vertices) for i in range(3)]
        hi = [max((obj.matrix_world @ v.co)[i] for v in me.vertices) for i in range(3)]
        entry["world_bbox_min"] = r3(lo)
        entry["world_bbox_max"] = r3(hi)
    if obj.type == "ARMATURE":
        entry["bones"] = len(obj.data.bones)
        entry["bone_names"] = [b.name for b in obj.data.bones]
    report["objects"].append(entry)

for act in bpy.data.actions:
    report["actions"].append({"name": act.name, "frame_range": r3(act.frame_range)})

arm = next(o for o in scene.objects if o.type == "ARMATURE")
report["armature"] = arm.name
report["scale"] = r3(arm.scale)
report["world_matrix_rows"] = [r3(row) for row in arm.matrix_world]
for bone in arm.data.bones:
    if bone.name.startswith("WPN") or bone.name in (
        "hand_r", "hand_l", "lowerarm_r", "lowerarm_l", "upperarm_r", "upperarm_l",
        "index_01_r", "thumb_01_r", "index_01_l", "thumb_01_l", "root", "pelvis",
    ):
        report["bones"][bone.name] = {
            "head": r3(arm.matrix_world @ bone.head_local),
            "tail": r3(arm.matrix_world @ bone.tail_local),
            "parent": bone.parent.name if bone.parent else None,
        }

actions = {a.name: a for a in bpy.data.actions}
idle = actions.get("M4_idle")
if idle and arm.animation_data:
    arm.animation_data.action = idle
    if idle.slots:
        arm.animation_data.action_slot = idle.slots[0]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    for bone in arm.pose.bones:
        if bone.name.startswith("WPN") or bone.name in ("hand_r", "hand_l", "lowerarm_r", "lowerarm_l"):
            report["pose_idle0"][bone.name] = {
                "head_world": r3(arm.matrix_world @ bone.head),
                "tail_world": r3(arm.matrix_world @ bone.tail),
                "matrix_rows": [r3(row) for row in bone.matrix],
            }

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "arms_structure.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print("ASH12_ARMS_OBJECTS", [(o["name"], o["type"]) for o in report["objects"]])
print("ASH12_ARMS_ACTIONS", [a["name"] for a in report["actions"]])
print("ASH12_ARMS_DONE")
