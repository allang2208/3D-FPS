"""Save the Fab surfaces, mesh, named grip sockets, flame socket and icon in the isolated UE host."""
import json
import os
from pathlib import Path
import unreal as u

root=Path(os.environ["FPS_PROJECT_ROOT"])
source=root/"SourceAssets/WoodenTorch20261122/FabHandheldR2/Export"
batch=Path(os.environ["TORCH_BATCH"])
folder="/Game/Weapons/WoodenTorch20261122"
revision=folder+"/FabHandheldR2"
icons="/Game/ColdSteelData/Icons"
tools=u.AssetToolsHelpers.get_asset_tools()
lib=u.EditorAssetLibrary
edit=u.MaterialEditingLibrary
saved=[]
def save(obj):
    if not lib.save_loaded_asset(obj,False): raise RuntimeError("Unable to save "+obj.get_path_name())
    saved.append(obj.get_path_name())
def take(filename, target, options=None):
    task=u.AssetImportTask()
    task.filename=str(source/filename);task.destination_path=target;task.destination_name=Path(filename).stem
    task.automated=True;task.replace_existing=True;task.save=False
    if options: task.options=options
    tools.import_asset_tasks([task])
    asset=lib.load_asset(target+"/"+task.destination_name)
    if asset is None: raise RuntimeError("Missing import "+filename)
    return asset
def connect(a,out,b,pin):
    if not edit.connect_material_expressions(a,out,b,pin):raise RuntimeError("Cannot connect material pin "+pin)
def output(node,channel,prop):
    if not edit.connect_material_property(node,channel,prop): raise RuntimeError("Cannot connect "+str(prop))
materials={}
for part in ("Wood","Rope","Cloth"):
    name="M_HandheldTorch_"+part
    mat=lib.load_asset(revision+"/"+name) if lib.does_asset_exist(revision+"/"+name) else tools.create_asset(name,revision,u.Material,u.MaterialFactoryNew())
    edit.delete_all_material_expressions(mat)
    masked=part=="Cloth"
    mat.set_editor_property("two_sided",masked)
    mat.set_editor_property("blend_mode",u.BlendMode.BLEND_MASKED if masked else u.BlendMode.BLEND_OPAQUE)
    slab=edit.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels,120,0)
    slab.set_editor_property("shading_model_override",u.MaterialShadingModel.MSM_DEFAULT_LIT)
    roles=["BaseColor","Normal","ORM"]+(["Opacity"] if masked else [])
    for row,role in enumerate(roles):
        tex=take(f"T_HandheldTorch_{part}_{role}.png",revision)
        if role!="BaseColor":
            tex.set_editor_property("srgb",False)
            tex.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_NORMALMAP if role=="Normal" else u.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("lod_group",u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if role=="Normal" else u.TextureGroup.TEXTUREGROUP_WEAPON)
        if role=="Normal":tex.set_editor_property("flip_green_channel",False)
        node=edit.create_material_expression(mat,u.MaterialExpressionTextureSample,-450,row*230)
        node.texture=tex
        node.sampler_type={"BaseColor":u.MaterialSamplerType.SAMPLERTYPE_COLOR,"Normal":u.MaterialSamplerType.SAMPLERTYPE_NORMAL}.get(role,u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        mapping={"BaseColor":[("RGB","BaseColor",u.MaterialProperty.MP_BASE_COLOR)],
                 "Normal":[("RGB","Normal",u.MaterialProperty.MP_NORMAL)],
                 "ORM":[("R",None,u.MaterialProperty.MP_AMBIENT_OCCLUSION),("G","Roughness",u.MaterialProperty.MP_ROUGHNESS),("B","Metallic",u.MaterialProperty.MP_METALLIC)],
                 "Opacity":[("R",None,u.MaterialProperty.MP_OPACITY_MASK)]}
        for channel,pin,prop in mapping[role]:
            if pin:connect(node,channel,slab,pin)
            output(node,channel,prop)
        save(tex)
    output(slab,"",u.MaterialProperty.MP_FRONT_MATERIAL)
    edit.recompile_material(mat)
    save(mat)
    materials[part]=mat
u.SystemLibrary.execute_console_command(None,"Interchange.FeatureFlags.Import.FBX 0")
opt=u.FbxImportUI()
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.static_mesh_import_data.combine_meshes=True; opt.static_mesh_import_data.auto_generate_collision=False
mesh=take("SM_WoodenTorch.fbx",folder,opt)
slots=[]
for i,slot in enumerate(mesh.get_editor_property("static_materials")):
    name=str(slot.get_editor_property("material_slot_name"))
    mesh.set_material(i,materials[name]); slots.append(name)
if set(slots)!=set(materials): raise RuntimeError("Incomplete FBX material slots "+str(slots))
fit=json.loads((source/"fit.json").read_text())
hands=json.loads((source/"hands.json").read_text())
sockets={"Grip":[0,0,0],"Flame":fit["flame_socket_ue_cm"],**hands["sockets_ue_cm"]}
for key,loc in sockets.items():
    socket=mesh.find_socket(key)
    if not socket:
        socket=u.new_object(u.StaticMeshSocket,outer=mesh)
        socket.set_editor_property("socket_name",key)
        mesh.add_socket(socket)
    socket.set_editor_property("relative_location",u.Vector(*loc))
save(mesh)
icon=take("ue_wooden_torch.png",icons)
icon.set_editor_property("lod_group",u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_EDITOR_ICON)
save(icon)
(batch/"surface-saved.json").write_text(json.dumps(dict(assets=saved,slots=slots,sockets=sockets),indent=2))
