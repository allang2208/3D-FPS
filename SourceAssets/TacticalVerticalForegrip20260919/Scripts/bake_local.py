"""Bake/export the locally authored candidate. Texture baking is production, not a preview."""
import bpy
import json
import numpy as np
import os
from pathlib import Path
ROOT=Path(os.environ.get('TACTICAL_GRIP_AUTHOR_ROOT',str(Path(__file__).resolve().parents[1])))
SOURCE=ROOT/"Source"
OUT=ROOT/"Export"
TEX=OUT/"Textures"
TEX.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/"TacticalVerticalForegrip_Construction.blend"))
parts=[o for o in bpy.context.scene.objects if o.type=="MESH"]
bpy.ops.object.select_all(action="DESELECT")
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join()
high=bpy.context.object
high.name="TacticalVerticalForegrip_SurfaceMaster"
high.data.calc_loop_triangles()
master_count=len(high.data.loop_triangles)
low=high.copy()
low.data=high.data.copy()
bpy.context.collection.objects.link(low)
low.name="SM_TacticalVerticalForegrip_Candidate"
bpy.ops.object.select_all(action="DESELECT")
low.select_set(True)
bpy.context.view_layer.objects.active=low
mod=low.modifiers.new("GameMeshReduction","DECIMATE")
mod.ratio=min(1.0,28000/master_count)
mod.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=mod.name)
low.data.materials.clear()
mat=bpy.data.materials.new("M_TacticalVerticalForegrip_Candidate")
mat.use_nodes=True
low.data.materials.append(mat)
for face in low.data.polygons:
    face.material_index=0
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.151917,island_margin=.012,area_weight=.1)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.scene.cursor.location=(0,0,0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=8
scene.render.bake.use_selected_to_active=True
scene.render.bake.use_clear=True
scene.render.bake.margin=12
scene.render.bake.cage_extrusion=.00055
scene.render.bake.max_ray_distance=.0014
scene.render.bake.normal_space="TANGENT"
SIZE=2048
target_node=mat.node_tree.nodes.new("ShaderNodeTexImage")
mat.node_tree.nodes.active=target_node
source_materials=list(high.data.materials)

def select_pair():
    bpy.ops.object.select_all(action="DESELECT")
    high.hide_set(False)
    high.hide_render=False
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active=low
def emission_override(channel):
    restored=[]
    for material in source_materials:
        nodes,links=material.node_tree.nodes,material.node_tree.links
        output=next(n for n in nodes if n.type=="OUTPUT_MATERIAL")
        bs=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
        original=output.inputs["Surface"].links[0].from_socket
        emission=nodes.new("ShaderNodeEmission")
        source=bs.inputs[channel]
        if source.is_linked:
            links.new(source.links[0].from_socket,emission.inputs["Color"])
        else:
            value=source.default_value
            emission.inputs["Color"].default_value=tuple(value) if channel=="Base Color" else (value,value,value,1)
        links.new(emission.outputs["Emission"],output.inputs["Surface"])
        restored.append((material,original,output,emission))
    return restored
def restore(records):
    for material,original,output,emission in records:
        material.node_tree.links.new(original,output.inputs["Surface"])
        material.node_tree.nodes.remove(emission)
def bake(key,channel=None):
    image=bpy.data.images.new("T_TacticalVerticalForegrip_"+key,width=SIZE,height=SIZE,alpha=False)
    image.colorspace_settings.name="sRGB" if key=="BaseColor" else "Non-Color"
    target_node.image=image
    records=emission_override(channel) if channel else []
    select_pair()
    print("BAKE_BEGIN "+key,flush=True)
    try:
        bpy.ops.object.bake(type="EMIT" if channel else "NORMAL")
    finally:
        restore(records)
    if key in ["BaseColor","Normal"]:
        image.filepath_raw=str(TEX/(image.name+".png"))
        image.file_format="PNG"
        image.save()
    print("BAKE_DONE "+key,flush=True)
    return image

base=bake("BaseColor","Base Color")
rough=bake("Roughness_Work","Roughness")
metal=bake("Metallic_Work","Metallic")
normal=bake("Normal")
count=SIZE*SIZE*4
r=np.empty(count,dtype=np.float32)
m=np.empty(count,dtype=np.float32)
rough.pixels.foreach_get(r)
metal.pixels.foreach_get(m)
packed=np.ones((SIZE*SIZE,4),dtype=np.float32)
packed[:,1]=r.reshape(-1,4)[:,0]
packed[:,2]=m.reshape(-1,4)[:,0]
mr=bpy.data.images.new("T_TacticalVerticalForegrip_MetalRough",width=SIZE,height=SIZE,alpha=False)
mr.colorspace_settings.name="Non-Color"
mr.pixels.foreach_set(packed.ravel())
mr.filepath_raw=str(TEX/(mr.name+".png"))
mr.file_format="PNG"
mr.save()
bpy.data.images.remove(rough)
bpy.data.images.remove(metal)
nodes,links=mat.node_tree.nodes,mat.node_tree.links
nodes.remove(target_node)
bs=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
for i,(key,img) in enumerate([("BaseColor",base),("MetalRough",mr),("Normal",normal)]):
    tex=nodes.new("ShaderNodeTexImage")
    tex.image=img
    tex.location=(-600,-i*220)
    if key=="BaseColor":
        links.new(tex.outputs["Color"],bs.inputs["Base Color"])
    elif key=="MetalRough":
        separate=nodes.new("ShaderNodeSeparateColor")
        separate.mode="RGB"
        links.new(tex.outputs["Color"],separate.inputs["Color"])
        links.new(separate.outputs["Green"],bs.inputs["Roughness"])
        links.new(separate.outputs["Blue"],bs.inputs["Metallic"])
    else:
        nm=nodes.new("ShaderNodeNormalMap")
        links.new(tex.outputs["Color"],nm.inputs["Color"])
        links.new(nm.outputs["Normal"],bs.inputs["Normal"])
high.hide_set(True)
high.hide_render=True
bpy.ops.object.select_all(action="DESELECT")
low.select_set(True)
bpy.context.view_layer.objects.active=low
bpy.context.view_layer.update()
bpy.ops.export_scene.fbx(
    filepath=str(OUT/"SM_TacticalVerticalForegrip_Candidate.fbx"),
    use_selection=True,object_types={"MESH"},axis_forward="-Y",axis_up="Z",
    bake_anim=False,mesh_smooth_type="FACE",use_tspace=True,path_mode="STRIP")
bpy.ops.export_scene.gltf(
    filepath=str(OUT/"TacticalVerticalForegrip_Candidate.glb"),
    export_format="GLB",use_selection=True,export_apply=True)
for reference in ["user_reference.png","three_views.png"]:
    ref_image=bpy.data.images.load(str(ROOT/"Reference"/reference),check_existing=True)
    ref_image.use_fake_user=True
bpy.ops.file.pack_all()
editable=SOURCE/"TacticalVerticalForegrip_Editable.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(editable))
low.data.calc_loop_triangles()
report={
    "status":"authored_baked_exported_not_tested",
    "route":"User-selected local Blender hard-surface authoring, UE/Vibe3D candidate preparation",
    "construction":str(SOURCE/"TacticalVerticalForegrip_Construction.blend"),
    "blend":str(editable),
    "game_triangles":len(low.data.loop_triangles),
    "master_triangles":master_count,
    "game_dimensions_cm":[float(x)*100 for x in low.dimensions],
    "textures":{key:str(TEX/("T_TacticalVerticalForegrip_"+key+".png")) for key in ["BaseColor","MetalRough","Normal"]},
    "texture_resolution":SIZE,
    "metal_rough_channels":{"R":"unused white","G":"roughness","B":"metallic"},
    "normal_convention":"OpenGL tangent; UE import flips green",
    "pivot":"top mounting saddle plane at Z=0, body extends -Z",
    "axes":"+X forward/ribbed narrow face; +Z up; Blender meters -> UE centimeters",
    "generator_result_used":False,
    "tests_run":False,"preview_rendered":False,
    "runtime_references_changed":False
}
(ROOT/"authoring_receipt.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("LOCAL_AUTHORING_COMPLETE "+json.dumps(report),flush=True)
