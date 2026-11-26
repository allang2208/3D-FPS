"""Save the dressed, fully skinned Jason R4 as an editable Blender source in its native pose."""
import bpy
import gzip
import json
import numpy as np
from pathlib import Path

root=Path(__file__).resolve().parents[3]
src=root/"SourceAssets/HillsVillageHighWall20261120/MasterArtisan"
revision=globals().get("head_revision","R1")
head_source=src/("Head"+revision) if revision!="R1" else src
outfit_source=src/globals().get("workwear_revision","")
smith=root/"SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit"
native=root/"SourceAssets/JasonStrong20261117/R2_LongLegs/textures"
bpy.ops.wm.open_mainfile(filepath=str(smith/"Smith_Body_Workwear.blend"))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects["Jason_NativeSkeleton"]
body=bpy.data.objects["SK_Smith_Body"]
for ob in list(bpy.context.scene.objects):
    if ob.type=="MESH" and ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
bones=json.loads((smith/"outfit.json").read_text())["bones"]
def collar_skin(mat,shader):
    """Mirror the narrow rest-space UE material blend on the editable head."""
    n=mat.node_tree.nodes;l=mat.node_tree.links
    def scalar(op,a,b):
        v=n.new("ShaderNodeMath");v.operation=op
        for i,s in enumerate((a,b)):
            if isinstance(s,(int,float)):v.inputs[i].default_value=s
            else:l.new(s,v.inputs[i])
        return v.outputs[0]
    attr=n.new("ShaderNodeAttribute");attr.attribute_name="artisan_rest_cm"
    xyz=n.new("ShaderNodeSeparateXYZ");l.new(attr.outputs["Vector"],xyz.inputs[0])
    x,y,z=xyz.outputs
    angle=scalar("ARCTAN2",scalar("SUBTRACT",x,.1),scalar("ADD",y,.85))
    uv=n.new("ShaderNodeCombineXYZ")
    l.new(scalar("ADD",.5,scalar("MULTIPLY",angle,.15915494)),uv.inputs[0])
    l.new(scalar("MINIMUM",1,scalar("MAXIMUM",0,scalar("DIVIDE",scalar("SUBTRACT",z,152.75),4.2))),uv.inputs[1])
    tex=n.new("ShaderNodeTexImage");tex.image=bpy.data.images.load(str(outfit_source/"T_ArtisanCollarSeam.png"),check_existing=True)
    l.new(uv.outputs[0],tex.inputs[0])
    distance=n.new("ShaderNodeMath");distance.operation="ABSOLUTE";l.new(scalar("SUBTRACT",z,154.75),distance.inputs[0])
    fade=n.new("ShaderNodeMapRange");fade.clamp=True;fade.interpolation_type="SMOOTHSTEP"
    l.new(distance.outputs[0],fade.inputs["Value"])
    for pin,val in (("From Min",.26),("From Max",1.65),("To Min",1.),("To Max",0.)):fade.inputs[pin].default_value=val
    for pin,replacement,kind in (("Base Color",tex.outputs["Color"],"RGBA"),("Normal",n.new("ShaderNodeNewGeometry").outputs["Normal"],"VECTOR"),("Roughness",.56,"FLOAT"),("Metallic",0.,"FLOAT")):
        dest=shader.inputs[pin]
        mix=n.new("ShaderNodeMix");mix.data_type=kind
        a,b=[v for v in mix.inputs if v.enabled and v.name in ("A","B")]
        if dest.is_linked:l.new(dest.links[0].from_socket,a)
        else:a.default_value=dest.default_value
        if isinstance(replacement,float):b.default_value=replacement
        else:l.new(replacement,b)
        l.new(fade.outputs["Result"],mix.inputs[0])
        l.new(next(o for o in mix.outputs if o.enabled),dest)

def surface(slot):
    if bpy.data.materials.get("Master | "+slot):return bpy.data.materials["Master | "+slot]
    existing=bpy.data.materials.get("M_Smith_"+slot)
    if existing and outfit_source.name=="WorkwearR6" and slot in ("Apron","Saddle"):
        mat=existing.copy();mat.name="Master | "+slot
        nodes=mat.node_tree.nodes;links=mat.node_tree.links
        shader=next(node for node in nodes if node.type=="BSDF_PRINCIPLED")
        rough=shader.inputs["Roughness"]
        remap=nodes.new("ShaderNodeMapRange")
        remap.inputs["To Min"].default_value=.48 if slot=="Apron" else .41
        remap.inputs["To Max"].default_value=.90 if slot=="Apron" else .86
        if rough.is_linked:links.new(rough.links[0].from_socket,remap.inputs["Value"])
        else:remap.inputs["Value"].default_value=rough.default_value
        links.new(remap.outputs["Result"],rough)
        shader.inputs["Specular IOR Level"].default_value=.30 if slot=="Apron" else .35
        return mat
    if existing:return existing
    mat=bpy.data.materials.new("Master | "+slot)
    mat.use_nodes=True
    nd=mat.node_tree.nodes
    links=mat.node_tree.links
    principled=nd.get("Principled BSDF")
    def image(path,port):
        t=nd.new("ShaderNodeTexImage")
        t.image=bpy.data.images.load(str(path),check_existing=True)
        links.new(t.outputs["Color"],port)
    if slot in ("Head","Neck","Indigo","Lapel","Flax","Hair"):
        folder=head_source if slot in ("Head","Neck") else outfit_source if slot=="Flax" else src
        image(folder/("T_Artisan"+slot+".png"),principled.inputs["Base Color"])
        if slot in ("Head","Neck"):
            n=nd.new("ShaderNodeNormalMap")
            image((head_source/"T_ArtisanHeadDetail.png") if slot=="Head" and revision in ("R2","R4") else (native/"T_Head_LOD2_N.png"),n.inputs["Color"])
            n.inputs["Color"].links[0].from_node.image.colorspace_settings.name="Non-Color"
            links.new(n.outputs["Normal"],principled.inputs["Normal"])
            if revision=="R4" and slot=="Head":
                split=nd.new("ShaderNodeSeparateColor")
                image(head_source/"T_ArtisanHeadORM.png",split.inputs["Color"])
                split.inputs["Color"].links[0].from_node.image.colorspace_settings.name="Non-Color"
                links.new(split.outputs["Green"],principled.inputs["Roughness"])
                links.new(split.outputs["Blue"],principled.inputs["Metallic"])
    elif "MI_EyeL_Baked" in slot:
        image(native/"T_EyeScleraL_BC.png",principled.inputs["Base Color"])
    elif "MI_Teeth" in slot:
        image(native/"T_Teeth_BC.png",principled.inputs["Base Color"])
    elif slot.startswith("/Game/") or slot=="Lens":
        principled.inputs["Alpha"].default_value=.055 if slot=="Lens" else .018
    else:
        colors={"Frame":(.022,.019,.015),"Toolwood":(.29,.14,.049),"Iron":(.14,.15,.16),"WaxThread":(.16,.092,.045)}
        principled.inputs["Base Color"].default_value=(*colors.get(slot,(.06,.05,.04)),1)
    if slot in ("Head","Neck") and outfit_source.name=="WorkwearR6":collar_skin(mat,principled)
    return mat

for name in ("Head","Workwear"):
    with gzip.open((head_source if name=="Head" else outfit_source)/(name+".json.gz"),"rt",encoding="utf8") as f:d=json.load(f)
    mesh=bpy.data.meshes.new("Master "+name)
    pos=np.asarray(d["p"])*.01
    faces=np.asarray(d["tri"])[:,::-1]
    mesh.from_pydata(pos.tolist(),[],faces.tolist())
    mesh.update()
    if name=="Head" and outfit_source.name=="WorkwearR6":
        attr=mesh.attributes.new("artisan_rest_cm","FLOAT_VECTOR","POINT")
        attr.data.foreach_set("vector",np.asarray(d["p"],np.float32).ravel())
    for slot in d["materials"]:mesh.materials.append(surface(slot))
    mesh.polygons.foreach_set("material_index",np.int32(d["m"]))
    mesh.polygons.foreach_set("use_smooth",[True]*len(faces))
    uv=np.asarray(d["uv"],np.float32);uv[:,1]=1-uv[:,1]
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv",uv[faces].ravel())
    mesh.normals_split_custom_set_from_vertices(d["n"])
    ob=bpy.data.objects.new("SK_MasterArtisan_"+name,mesh)
    bpy.context.collection.objects.link(ob)
    for b in bones:ob.vertex_groups.new(name=b["name"])
    for i,weights in enumerate(d["w"]):
        for k,weight in weights:ob.vertex_groups[k].add([i],weight,"REPLACE")
    mod=ob.modifiers.new("Jason R4 standing rig","ARMATURE");mod.object=rig
    ob["UE_asset"]="/Game/Characters/VillageMasterArtisan/"+ob.name
bpy.context.scene["preview_note"]="Mechanical workshop master, Jason R4 body with independent head and workwear."
out=outfit_source if outfit_source!=src else head_source
bpy.ops.wm.save_as_mainfile(filepath=str(out/"MasterArtisan.blend"),compress=True,relative_remap=True)
