"""Give the ASH-12's Blender materials the same gunmetal treatment as the engine
side, so renders and the inventory icon stop showing the source decal skin.

Run: blender --background --factory-startup --python-exit-code 1 --python metal_materials.py
"""
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

# material -> (base colour, roughness, metallic)
METALS = {
    "M_ASH12_Upper": ((0.085, 0.090, 0.098), 0.45, 0.70),
    "M_ASH12_Lower": ((0.080, 0.085, 0.092), 0.47, 0.70),
    "M_ASH12_Front": ((0.090, 0.095, 0.103), 0.45, 0.70),
    "M_ASH12_Sights": ((0.065, 0.068, 0.072), 0.50, 0.65),
    "M_ASH12_Flash_Hider": ((0.320, 0.330, 0.340), 0.32, 0.90),
    "M_ASH12_Magazine": ((0.050, 0.050, 0.052), 0.60, 0.05),
    "M_ASH12_Magazine_Base": ((0.044, 0.044, 0.046), 0.62, 0.05),
}

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
for name, (colour, roughness, metallic) in METALS.items():
    material = bpy.data.materials.get(name)
    if not material:
        print("ASH12_METAL missing", name)
        continue
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (colour[0], colour[1], colour[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    material.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    print("ASH12_METAL", name, colour, roughness, metallic)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
print("ASH12_METAL_DONE")
