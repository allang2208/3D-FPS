import math
import bpy
import bmesh
import json
import os

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
SRC = os.environ.get("ALICE_SRC_BLEND", os.path.join(ROOT, "AliceBackpack_baked.blend"))
OUT_OBJ = os.environ.get("ALICE_EXPORT_OBJ", os.path.join(ROOT, "AliceBackpack_ue.obj"))
RECEIPT = os.environ.get("ALICE_EXPORT_RECEIPT", os.path.join(ROOT, "export_ue_receipt.json"))

bpy.ops.wm.open_mainfile(filepath=SRC)
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name in ("SM_AliceBackpack", "SM_AliceBackpack_Detail"))

# Duplicate for a centimetre-scale OBJ; UE's OBJ importer treats one unit as 1 cm.
dup = obj.copy()
dup.data = obj.data.copy()
bpy.context.collection.objects.link(dup)
dup.name = "SM_AliceBackpack_UE"
# OBJ is consumed as Y-up by UE. Pre-rotate Blender Z-up to Y-up so the
# importer restores an upright Z-up mesh instead of laying it on its back.
dup.rotation_euler = (math.radians(-90.0), 0.0, 0.0)
bpy.context.view_layer.objects.active = dup
bpy.ops.object.select_all(action="DESELECT")
dup.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
dup.scale = (100.0, 100.0, 100.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Make the asset pivot the bbox centre; this keeps the outfit mount offset
# independent of where the original OBJ had its origin.
lo = [min(v.co[i] for v in dup.data.vertices) for i in range(3)]
hi = [max(v.co[i] for v in dup.data.vertices) for i in range(3)]
centre = [(lo[i] + hi[i]) * 0.5 for i in range(3)]
for v in dup.data.vertices:
    v.co.x -= centre[0]
    v.co.y -= centre[1]
    v.co.z -= centre[2]
dup.data.update()

# Plain export materials: the real PBR assets are created directly in UE.
for i, name in enumerate(["Canvas", "Webbing", "Leather", "Metal"]):
    mat = bpy.data.materials.new("AliceExport_" + name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.2, 0.2, 0.15, 1)
    dup.data.materials[i] = mat

bpy.ops.wm.obj_export(
    filepath=OUT_OBJ,
    export_selected_objects=True,
    apply_modifiers=True,
    export_uv=True,
    export_normals=True,
    export_materials=True,
    path_mode="AUTO",
)

bbox_min = [min((dup.matrix_world @ v.co)[i] for v in dup.data.vertices) for i in range(3)]
bbox_max = [max((dup.matrix_world @ v.co)[i] for v in dup.data.vertices) for i in range(3)]
receipt = {
    "obj": OUT_OBJ,
    "bbox_cm_min": bbox_min,
    "bbox_cm_max": bbox_max,
    "dimensions_cm": [bbox_max[i] - bbox_min[i] for i in range(3)],
    "verts": len(dup.data.vertices),
    "polys": len(dup.data.polygons),
    "slots": [m.name for m in dup.data.materials],
    "uv_layers": [layer.name for layer in dup.data.uv_layers],
}
with open(RECEIPT, "w", encoding="utf-8") as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
print("ALICE_EXPORT_UE " + json.dumps(receipt, ensure_ascii=False, default=str))
