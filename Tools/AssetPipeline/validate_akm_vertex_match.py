import bpy
import json
import math
from pathlib import Path

SOURCE = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend")
OUTPUT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\akm_vertex_match_validation.json")
CLIPS = ("idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "draw", "holster", "inspect")


def action_slot_for(action, object_name):
    wanted = f"OB{object_name}"
    for slot in action.slots:
        if slot.identifier == wanted:
            return slot
    raise RuntimeError(f"Action {action.name} has no slot for {object_name}")


def evaluated_world_vertices(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    result = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    evaluated.to_mesh_clear()
    return result


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source_rigs = [bpy.data.objects["ArmsRig"], bpy.data.objects["WeaponRig"]]
target_rig = bpy.data.objects["SK_AKM_Viewmodel"]
pairs = []
for target in bpy.data.objects:
    if target.type != "MESH" or target.parent != target_rig:
        continue
    source_name = target.name.removesuffix(".001")
    pairs.append((bpy.data.objects[source_name], target))

depsgraph = bpy.context.evaluated_depsgraph_get()
report = {"source": str(SOURCE), "clips": {}}
for clip in CLIPS:
    source_action = bpy.data.actions[clip]
    for rig in source_rigs:
        rig.animation_data.action = source_action
        rig.animation_data.action_slot = action_slot_for(source_action, rig.name)
    target_action = bpy.data.actions[f"AKM_{clip}"]
    target_rig.animation_data.action = target_action
    target_rig.animation_data.action_slot = target_action.slots[0]
    start, end = [int(round(value)) for value in source_action.frame_range]
    frames = sorted(set((start, (start + end) // 2, end)))
    clip_samples = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph.update()
        mesh_results = []
        for source, target in pairs:
            source_vertices = evaluated_world_vertices(source, depsgraph)
            target_vertices = evaluated_world_vertices(target, depsgraph)
            distances = [(a - b).length for a, b in zip(source_vertices, target_vertices)]
            mesh_results.append({
                "mesh": source.name,
                "vertex_count": len(distances),
                "rms_m": math.sqrt(sum(value * value for value in distances) / len(distances)),
                "max_m": max(distances),
            })
        clip_samples.append({"frame": frame, "meshes": mesh_results})
    report["clips"][clip] = clip_samples

OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
