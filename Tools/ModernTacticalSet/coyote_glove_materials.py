"""Physical-scale TS01 glove finishes shared by the artist models and the game."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113/CoyoteGlovesR2"
# sRGB albedo, roughness, sheen, resolution. Each tile represents 4 cm.
SURFACES={
    "Knit": ((130,113,78),.84,.24,2048),
    "Suede": ((106,89,64),.91,.31,2048),
    "Stretch": ((99,85,61),.86,.20,1024),
    "Rubber": ((93,77,54),.61,.00,1024),
    "Webbing": ((117,99,70),.83,.17,1024),
    "Thread": ((136,118,84),.79,.19,512),
    "Label": ((104,87,62),.67,.00,1024),
}


def create(surfaces=SURFACES,texture_root=ROOT,prefix="CG_",tile_cm=4.):
    import bpy
    occlusion=bpy.data.node_groups.get("glTF Material Output")
    if occlusion is None:
        occlusion=bpy.data.node_groups.new("glTF Material Output","ShaderNodeTree")
        occlusion.interface.new_socket(name="Occlusion",in_out="INPUT",socket_type="NodeSocketFloat")
    result={}
    for kind,(color,roughness,sheen,size) in surfaces.items():
        name=prefix+kind
        mat=bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes=True
        mat.diffuse_color=tuple(((c/255+.055)/1.055)**2.4 for c in color)+(1.,)
        nodes=mat.node_tree.nodes;nodes.clear()
        link=mat.node_tree.links.new
        out=nodes.new("ShaderNodeOutputMaterial")
        bs=nodes.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Roughness"].default_value=roughness
        bs.inputs["Specular IOR Level"].default_value=.29
        bs.inputs["Sheen Weight"].default_value=sheen
        link(bs.outputs["BSDF"],out.inputs["Surface"])
        for channel in ("BaseColor","NormalGL","ORM"):
            tx=nodes.new("ShaderNodeTexImage")
            tx.label=channel
            tx.image=bpy.data.images.load(str(texture_root/"Textures"/f"{name}_{channel}.png"),check_existing=True)
            tx.image.colorspace_settings.name="sRGB" if channel=="BaseColor" else "Non-Color"
            tx.extension="EXTEND" if kind=="Label" else "REPEAT"
            if channel=="BaseColor":
                link(tx.outputs["Color"],bs.inputs["Base Color"])
            elif channel=="NormalGL":
                normal=nodes.new("ShaderNodeNormalMap")
                link(tx.outputs["Color"],normal.inputs["Color"]);link(normal.outputs[0],bs.inputs["Normal"])
            else:
                sep=nodes.new("ShaderNodeSeparateColor")
                link(tx.outputs["Color"],sep.inputs[0])
                link(sep.outputs["Green"],bs.inputs["Roughness"]);link(sep.outputs["Blue"],bs.inputs["Metallic"])
                group=nodes.new("ShaderNodeGroup");group.node_tree=occlusion
                link(sep.outputs["Red"],group.inputs["Occlusion"])
        mat["PhysicalTile_cm"]=tile_cm
        result[name]=mat
    return result
