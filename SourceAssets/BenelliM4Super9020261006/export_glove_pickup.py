"""Export the cuff-fixed hardknuckle glove as the static pickup FBX (M4 space)."""
import bpy, json
import numpy as np
from pathlib import Path

O = Path("D:/FPS3D/FPSGAME/SourceAssets/BenelliM4Super9020261006")
d = json.loads((O / "EquipmentAuthored" / "M4_ue_hardknuckle_gloves.json").read_text())

bpy.ops.wm.read_factory_settings(use_empty=True)
# UE clockwise faces require the handedness reflection when entering Blender.
# Without it FBX exports an inside-out glove even when the UE source is correct.
verts = (np.asarray(d["positions"]) * np.array([0.01, -0.01, 0.01])).tolist()
faces = np.asarray(d["triangles"]).tolist()
mesh = bpy.data.meshes.new("SM_ue_hardknuckle_gloves")
mesh.from_pydata(verts, [], faces); mesh.update()
obj = bpy.data.objects.new("SM_ue_hardknuckle_gloves", mesh)
bpy.context.collection.objects.link(obj)
layer = mesh.uv_layers.new(name="UVMap")
for face, coords in zip(mesh.polygons, d["uv"]):
    for li, (u_, v_) in zip(face.loop_indices, coords):
        layer.data[li].uv = (u_, 1 - v_)
mesh.materials.append(bpy.data.materials.new("glove_hardknuckle"))
for f in mesh.polygons: f.use_smooth = True
mesh.normals_split_custom_set((np.asarray(d["normals"]).reshape(-1, 3) * np.array([1.0, -1.0, 1.0])).tolist())
obj.select_set(True); bpy.context.view_layer.objects.active = obj
out = O / "Exports" / "SM_ue_hardknuckle_gloves.fbx"
out.parent.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(out), use_selection=True, apply_scale_options="FBX_SCALE_NONE",
                         object_types={"MESH"}, use_mesh_modifiers=False, add_leaf_bones=False,
                         axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE")
print("GLOVE_PICKUP_FBX_EXPORTED", out)
