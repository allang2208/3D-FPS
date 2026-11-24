"""Author the two scoped ADS meshes from the Frontier sight and mounting shoe."""
from pathlib import Path
import json
import runpy
import bpy
from mathutils import Vector

source = Path(__file__).resolve().parent
export_dir = source / "Export"
export_dir.mkdir(exist_ok=True)
parts = runpy.run_path(str(source.parent / "CommonModsR1/author.py"))
# Blender Y is opposite to the bow-local Y in UE. Both scopes share the draw plane.
center = parts["AIM"] + Vector((0., 2.30, 0.))
yaw = 5.
options = {}
for part_id, name, power in (
    ("bow_clearfield_2x", "SM_Frontier_Clearfield2x", 2),
    ("bow_farwatch_4x", "SM_Frontier_Farwatch4x", 4),
):
    optic = parts["make_optic"](power, name, center, yaw, export_dir)
    options[part_id] = {"mesh": name, "power": power}
    optic.hide_set(power == 4)
    optic.hide_render = power == 4

for image in bpy.data.images:
    if image.source == "FILE" and not image.packed_file and Path(bpy.path.abspath(image.filepath)).is_file():
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(source / "Frontier_ScopedMounts.blend"))
manifest = {"options": options, "sight_cm": [round(center.x,3), round(-center.y,3), round(center.z,3)],
            "ads_rotation_deg": [0, yaw, 0]}
(source / "parts.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
