import bpy
import json
from pathlib import Path
from mathutils import Vector

SOURCE = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend")
OUTPUT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\akm_bake_validation.json")
CLIPS = ("idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "draw", "holster", "inspect")

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects["SK_AKM_Viewmodel"]
meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.parent == rig and not obj.hide_render]
depsgraph = bpy.context.evaluated_depsgraph_get()


def posed_bounds():
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


report = {"source": str(SOURCE), "clips": {}}
for clip in CLIPS:
    action = bpy.data.actions[f"AKM_{clip}"]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    start, end = [int(round(value)) for value in action.frame_range]
    frames = sorted(set((start, (start + end) // 2, end)))
    samples = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        depsgraph.update()
        minimum, maximum = posed_bounds()
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
