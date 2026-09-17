"""Measure the accepted M4 host: where the M4 grip / handguard / magazine sit in
pose space at idle frame 0, plus the hand bone frames a new rifle must fit.

Run: blender --background --factory-startup --python-exit-code 1 --python measure_host.py
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
arm = bpy.data.objects["SK_M4_Infima"]
idle = bpy.data.actions["M4_idle"]
if not arm.animation_data:
    arm.animation_data_create()
arm.animation_data.action = idle
if idle.slots:
    arm.animation_data.action_slot = idle.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()

dg = bpy.context.evaluated_depsgraph_get()

WATCH = [
    "M4_M4 Body_Export", "M4_Magazine Light.003_Export", "M4_Grip Default Unreal_Export",
    "M4_Handguard Kmode Unreal_Export", "M4_Stock Classic Unreal_Export",
    "M4_Trigger Straight Unreal_Export", "M4_Flash Hider Unreal_Export",
    "SM_M4_RearSight", "SM_M4_FrontSight", "SK_Manny_Arms_Export",
]

report = {"reference": BLEND, "frame": 0, "action": idle.name, "parts": {}, "bones": {}}


def bbox_of(obj):
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    lo = [round(min(p[i] for p in pts), 5) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 5) for i in range(3)]
    ev.to_mesh_clear()
    return lo, hi


def matrix_rows(m):
    return [[round(float(c), 6) for c in row] for row in m]


for name in WATCH:
    obj = bpy.data.objects.get(name)
    if not obj:
        continue
    lo, hi = bbox_of(obj)
    report["parts"][name] = {
        "bbox_min": lo, "bbox_max": hi,
        "size": [round(hi[i] - lo[i], 5) for i in range(3)],
        "center": [round((hi[i] + lo[i]) / 2, 5) for i in range(3)],
    }

# M4 reference length across every M4 part in the scene.
lows, highs = [], []
for obj in scene.objects:
    if obj.type == "MESH" and ("M4_" in obj.name or obj.name.startswith("SM_M4_")) and not obj.hide_render:
        lo, hi = bbox_of(obj)
        lows.append(lo)
        highs.append(hi)
if lows:
    lo = [min(v[i] for v in lows) for i in range(3)]
    hi = [max(v[i] for v in highs) for i in range(3)]
    report["m4_total_bbox_min"] = lo
    report["m4_total_bbox_max"] = hi
    report["m4_total_size"] = [round(hi[i] - lo[i], 5) for i in range(3)]

for bone in arm.pose.bones:
    if bone.name.startswith("WPN") or bone.name in (
        "hand_r", "hand_l", "lowerarm_r", "lowerarm_l", "upperarm_r", "upperarm_l",
        "index_01_r", "index_02_r", "index_03_r", "thumb_01_r", "thumb_02_r", "thumb_03_r",
        "index_01_l", "index_02_l", "index_03_l", "thumb_01_l", "thumb_02_l", "thumb_03_l",
        "middle_01_r", "middle_01_l", "pinky_01_r", "pinky_01_l", "ring_01_r", "ring_01_l",
        "clavicle_r", "clavicle_l", "ik_hand_gun", "VM_Root",
    ):
        report["bones"][bone.name] = {
            "head": [round(float(c), 5) for c in (arm.matrix_world @ bone.head)],
            "tail": [round(float(c), 5) for c in (arm.matrix_world @ bone.tail)],
            "matrix_pose": matrix_rows(bone.matrix),
            "matrix_rest": matrix_rows(arm.data.bones[bone.name].matrix_local),
        }

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "host_measure.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)

print("ASH12_HOST_PARTS")
for k, v in report["parts"].items():
    print("  %-34s min=%s max=%s size=%s" % (k, v["bbox_min"], v["bbox_max"], v["size"]))
print("  M4_TOTAL min=%s max=%s size=%s" % (report.get("m4_total_bbox_min"), report.get("m4_total_bbox_max"), report.get("m4_total_size")))
print("ASH12_HOST_BONES")
for k in ("hand_r", "hand_l", "index_01_r", "index_01_l", "thumb_01_r", "thumb_01_l", "WPN_root", "WPN_SOCKET_Magazine", "WPN_Trigger"):
    b = report["bones"].get(k)
    if b:
        print("  %-22s head=%s tail=%s" % (k, b["head"], b["tail"]))
print("ASH12_HOST_DONE")
