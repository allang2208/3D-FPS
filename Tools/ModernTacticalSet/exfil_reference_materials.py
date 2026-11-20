"""The ten surface slots shared by the source meshes, inventory view and UE packages."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113/ExfilReferenceR4"
# The first entry is the exterior shell. Preserve the order on all three LODs.
SURFACES={
    "Composite": ((153,125,90),.82,.0,2048,8.0),
    "Polymer": ((141,112,83),.57,.0,1024,4.0),
    "Rubber": ((70,57,48),.80,.0,1024,4.0),
    "Webbing": ((125,105,78),.87,.0,1024,4.0),
    "LoopPile": ((126,104,76),.94,.0,1024,4.0),
    "PadMesh": ((43,41,37),.91,.0,1024,4.0),
    "Metal": ((62,59,54),.39,.68,512,4.0),
    "Label": ((62,58,55),.63,.0,1024,4.0),
    "Stitch": ((155,130,92),.86,.0,512,4.0),
    "DarkPolymer": ((60,52,44),.62,.0,1024,4.0),
}
CLOTH_SHEEN={"Webbing":.12,"LoopPile":.20,"PadMesh":.12,"Stitch":.13}


def create():
    import bpy
    result={}
    for key,(color,rough,metal,_resolution,scale) in SURFACES.items():
        name="H1_"+key
        mat=bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes=True
        mat.diffuse_color=tuple(((v/255+.055)/1.055)**2.4 for v in color)+(1.,)
        nodes=mat.node_tree.nodes
        nodes.clear()
        output=nodes.new("ShaderNodeOutputMaterial")
        shader=nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Roughness"].default_value=rough
        shader.inputs["Metallic"].default_value=metal
        shader.inputs["Specular IOR Level"].default_value=.26 if key not in ("Metal","Label") else .4
        if key in CLOTH_SHEEN:
            shader.inputs["Sheen Weight"].default_value=CLOTH_SHEEN[key]
            shader.inputs["Sheen Tint"].default_value=mat.diffuse_color
        links=mat.node_tree.links
        links.new(shader.outputs["BSDF"],output.inputs["Surface"])
        for channel in ("BaseColor","NormalGL","ORM"):
            file=ROOT/"Textures"/f"H1_{key}_{channel}.png"
            tex=nodes.new("ShaderNodeTexImage")
            tex.label=channel
            tex.image=bpy.data.images.load(str(file),check_existing=True)
            tex.extension="EXTEND" if key=="Label" else "REPEAT"
            if channel!="BaseColor":
                tex.image.colorspace_settings.name="Non-Color"
            if channel=="BaseColor":
                links.new(tex.outputs["Color"],shader.inputs["Base Color"])
            elif channel=="NormalGL":
                normal=nodes.new("ShaderNodeNormalMap")
                links.new(tex.outputs["Color"],normal.inputs["Color"])
                links.new(normal.outputs["Normal"],shader.inputs["Normal"])
            else:
                channels=nodes.new("ShaderNodeSeparateColor")
                links.new(tex.outputs["Color"],channels.inputs[0])
                links.new(channels.outputs["Green"],shader.inputs["Roughness"])
                links.new(channels.outputs["Blue"],shader.inputs["Metallic"])
        mat["PhysicalTile_cm"]=scale
        result[key]=mat
    return result
