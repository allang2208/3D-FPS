import bpy
import json
import math
import os
from mathutils import Vector

SRC = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019\AliceBackpack_raw.blend"
OUT_DIR = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
TARGET_HEIGHT_M = 0.46
MAT_NAMES = ["M_Alice_Canvas", "M_Alice_Webbing", "M_Alice_Leather", "M_Alice_Metal"]
OLD_TO_NEW = {0: 0, 1: 1, 2: 0, 3: 0, 4: 1, 5: 3, 6: 2}

os.makedirs(OUT_DIR, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
me = obj.data

# Original material order: lambert2SG, lambert3SG, lambert4SG,
# lambert6SG, lambert5SG, lambert8SG, lambert7SG.
old_slots = [slot.material.name if slot.material else slot.name for slot in obj.material_slots]
assert len(old_slots) == 7, old_slots

# Rotate Y-up/Z-back source into UE/Z-up with the padded back facing +Y.
obj.rotation_mode = "XYZ"
obj.rotation_euler = (math.radians(90.0), 0.0, math.radians(180.0))
bpy.context.view_layer.update()
height = (obj.matrix_world @ Vector(obj.bound_box[0])).z
zs = [(obj.matrix_world @ Vector(c)).z for c in obj.bound_box]
height = max(zs) - min(zs)
scale = TARGET_HEIGHT_M / height
obj.scale = (scale, scale, scale)
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# Center origin on the object's world-space bounding-box center.
corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
center = sum(corners, Vector()) / 8.0
bpy.context.scene.cursor.location = center
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Build four material slots and remap face material indices.
old_indices = [p.material_index for p in me.polygons]
new_mats = []
for name in MAT_NAMES:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (0.5, 0.5, 0.5, 1.0)
    new_mats.append(mat)

me.materials.clear()
for mat in new_mats:
    me.materials.append(mat)
for p, old in zip(me.polygons, old_indices):
    p.material_index = OLD_TO_NEW[old]

# Keep the authored UV map; make object/mesh names explicit.
obj.name = "SM_AliceBackpack"
me.name = "SM_AliceBackpack"
for p in me.polygons:
    pass

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "AliceBackpack_prepared.blend"))

# Export the transformed, four-slot source for the UE importer.
bpy.ops.wm.obj_export(
    filepath=os.path.join(OUT_DIR, "AliceBackpack_prepared.obj"),
    export_selected_objects=True,
    apply_modifiers=True,
    export_uv=True,
    export_normals=True,
    export_materials=True,
    path_mode="AUTO",
)

bbox_min = [min((obj.matrix_world @ v.co)[i] for v in me.vertices) for i in range(3)]
bbox_max = [max((obj.matrix_world @ v.co)[i] for v in me.vertices) for i in range(3)]
receipt = {
    "source": SRC,
    "target_height_m": TARGET_HEIGHT_M,
    "scale": scale,
    "bbox_min": bbox_min,
    "bbox_max": bbox_max,
    "dimensions": [bbox_max[i] - bbox_min[i] for i in range(3)],
    "old_slots": old_slots,
    "new_slots": [{"index": i, "name": m.name} for i, m in enumerate(new_mats)],
    "mapping": {old_slots[k]: MAT_NAMES[v] for k, v in OLD_TO_NEW.items()},
    "verts": len(me.vertices),
    "polys": len(me.polygons),
    "uv_layers": [layer.name for layer in me.uv_layers],
}
with open(os.path.join(OUT_DIR, "prepare_receipt.json"), "w", encoding="utf-8") as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
print("ALICE_PREP " + json.dumps(receipt, ensure_ascii=False, default=str))