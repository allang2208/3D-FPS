import bpy
import json
from pathlib import Path

SOURCE = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend")
OUTPUT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\akm_match_details.json")


def matrix_rows(matrix):
    return [[float(value) for value in row] for row in matrix]


def max_matrix_delta(a, b):
    return max(abs(a[row][column] - b[row][column]) for row in range(4) for column in range(4))


def slot(action, name):
    wanted = f"OB{name}"
    return next(value for value in action.slots if value.identifier == wanted)


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
target_rig = bpy.data.objects["SK_AKM_Viewmodel"]
source_rigs = [bpy.data.objects["ArmsRig"], bpy.data.objects["WeaponRig"]]
source_action = bpy.data.actions["idle"]
for rig in source_rigs:
    rig.animation_data.action = source_action
    rig.animation_data.action_slot = slot(source_action, rig.name)
target_action = bpy.data.actions["AKM_idle"]
target_rig.animation_data.action = target_action
target_rig.animation_data.action_slot = target_action.slots[0]
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()

report = {"rigs": {}, "bones": {}, "meshes": {}}
for rig in [*source_rigs, target_rig]:
    report["rigs"][rig.name] = matrix_rows(rig.matrix_world)
for source, names in ((source_rigs[0], ("root", "hand_l", "hand_r")), (source_rigs[1], ("root", "magazine", "bolt"))):
    for name in names:
        target_name = name if source.name == "ArmsRig" else f"WPN_{name}"
        desired = target_rig.matrix_world.inverted() @ source.matrix_world @ source.pose.bones[name].matrix
        actual = target_rig.pose.bones[target_name].matrix
        desired_rest = target_rig.matrix_world.inverted() @ source.matrix_world @ source.data.bones[name].matrix_local
        actual_rest = target_rig.data.bones[target_name].matrix_local
        report["bones"][target_name] = {
            "desired": matrix_rows(desired),
            "actual": matrix_rows(actual),
            "max_delta": max_matrix_delta(desired, actual),
            "desired_rest": matrix_rows(desired_rest),
            "actual_rest": matrix_rows(actual_rest),
            "rest_max_delta": max_matrix_delta(desired_rest, actual_rest),
        }

depsgraph = bpy.context.evaluated_depsgraph_get()
for source_name in ("AKM_Classic_Body", "SK_FP_CH_Default_Cubic"):
    source = bpy.data.objects[source_name]
    target = bpy.data.objects[f"{source_name}.001"]
    item = {}
    for label, obj in (("source", source), ("target", target)):
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        item[label] = {
            "matrix_world": matrix_rows(evaluated.matrix_world),
            "raw_v0": list(obj.data.vertices[0].co),
            "eval_world_v0": list(evaluated.matrix_world @ mesh.vertices[0].co),
        }
        evaluated.to_mesh_clear()
    report["meshes"][source_name] = item

OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
