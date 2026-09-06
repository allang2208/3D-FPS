"""Export the approved, editable V07 source without rebuilding older candidates."""
from pathlib import Path
import bpy

base = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(base / "ore-spider-impact.blend"))
rig = bpy.data.objects["OreRig"]
rig.animation_data.action = bpy.data.actions["Idle"]
bpy.context.scene.frame_set(0)
bpy.context.scene.render.fps = 90
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        obj.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=str(base.parents[2] / "assets/models/ore_spider/ore_spider_v07_preview.glb"),
    export_format="GLB", use_selection=True, export_animations=True,
    export_animation_mode="ACTIONS", export_frame_range=False,
    export_force_sampling=True,
)
print("ORE_FINAL_EXPORT_PASS")
