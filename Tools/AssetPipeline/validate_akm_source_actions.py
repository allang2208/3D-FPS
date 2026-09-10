import bpy
import json
from pathlib import Path
from mathutils import Vector

SOURCE = Path(r"E:\3d\akm-classic-staging\akm-classic-unified.blend")
OUTPUT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\akm_source_action_validation.json")
CLIPS = ("idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "draw", "holster", "inspect")


def action_slot_for(action, object_name):
    wanted = f"OB{object_name}"
    for slot in action.slots:
        if slot.identifier == wanted:
            return slot
    raise RuntimeError(f"Action {action.name} has no slot for {object_name}")


def posed_bounds(meshes, depsgraph):
    minimum = Vector((1e9, 1e9, 1e9))
    maximum = Vector((-1e9, -1e9, -1e9))
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vertex in mesh.vertices:
            point = evaluated.matrix_world @ vertex.co
            minimum.x = min(minimum.x, point.x)
            minimum.y = min(minimum.y, point.y)
            minimum.z = min(minimum.z, point.z)
            maximum.x = max(maximum.x, point.x)
            maximum.y = max(maximum.y, point.y)
            maximum.z = max(maximum.z, point.z)
        evaluated.to_mesh_clear()
    return minimum, maximum


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rigs = [bpy.data.objects["ArmsRig"], bpy.data.objects["WeaponRig"]]
for rig in rigs:
    if rig.animation_data is None:
        rig.animation_data_create()
    for track in rig.animation_data.nla_tracks:
        track.mute = True

meshes = []
for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    if any(mod.type == "ARMATURE" and mod.object in rigs for mod in obj.modifiers):
        meshes.append(obj)

depsgraph = bpy.context.evaluated_depsgraph_get()
report = {"source": str(SOURCE), "meshes": [obj.name for obj in meshes], "clips": {}}
for clip in CLIPS:
    action = bpy.data.actions[clip]
    for rig in rigs:
        rig.animation_data.action = action
        rig.animation_data.action_slot = action_slot_for(action, rig.name)
    start, end = [int(round(value)) for value in action.frame_range]
    frames = sorted(set((start, (start + end) // 2, end)))
    samples = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph.update()
        minimum, maximum = posed_bounds(meshes, depsgraph)
        samples.append({
            "frame": frame,
            "min": [round(value, 5) for value in minimum],
            "max": [round(value, 5) for value in maximum],
            "center": [round(value, 5) for value in (minimum + maximum) * 0.5],
            "extent": [round(value, 5) for value in (maximum - minimum) * 0.5],
        })
    report["clips"][clip] = samples

OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
