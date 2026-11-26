import bpy
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath=r"D:/FPS3D/FPSGAME/SourceAssets/FieldHat20261019/ue_field_hat-icon.blend")
for m in bpy.data.objects["FieldHat"].data.materials:
    print("MATERIAL", m.name)
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            print("  TEX", n.name, n.image.name if n.image else None, n.image.colorspace_settings.name if n.image else None)
        if n.type == "BSDF_PRINCIPLED":
            print("  BASE", list(n.inputs["Base Color"].default_value), "ROUGH", n.inputs["Roughness"].default_value, "METAL", n.inputs["Metallic"].default_value)
