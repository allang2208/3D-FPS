"""Import the owned packages in an empty authoring host or in the current project."""
import json
import os
from pathlib import Path
import unreal as u

source = Path(os.environ["FPS_PROJECT_ROOT"]) / "SourceAssets/WoodenTorch20261122/Export"
batch = Path(os.environ["TORCH_BATCH"])
folder = "/Game/Weapons/WoodenTorch20261122"
icons = "/Game/ColdSteelData/Icons"
lib = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
u.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
def take(file, dest, options=None):
    task = u.AssetImportTask()
    task.filename, task.destination_path = str(source/file), dest
    task.destination_name = Path(file).stem
    task.automated, task.replace_existing, task.save = True, True, False
    if options:
        task.options = options
    tools.import_asset_tasks([task])
    obj = lib.load_asset(dest + "/" + Path(file).stem)
    if not obj: raise RuntimeError("Import failed " + file)
    return obj

opt = u.FbxImportUI()
opt.import_mesh = True
opt.import_as_skeletal = opt.import_materials = opt.import_textures = opt.import_animations = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.automated_import_should_detect_type = False
opt.static_mesh_import_data.combine_meshes = True
opt.static_mesh_import_data.auto_generate_collision = False
material_only = os.environ.get("TORCH_MATERIAL_ONLY") == "1"
if not material_only:
    mesh = take("SM_WoodenTorch.fbx", folder, opt)
results = []
mat = lib.load_asset(folder+"/M_WoodenTorch") if lib.does_asset_exist(folder+"/M_WoodenTorch") else tools.create_asset("M_WoodenTorch",folder,u.Material,u.MaterialFactoryNew())
edit = u.MaterialEditingLibrary
edit.delete_all_material_expressions(mat)
mat.set_editor_property("two_sided", True)
slab = edit.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels,0,0)
slab.set_editor_property("shading_model_override",u.MaterialShadingModel.MSM_DEFAULT_LIT)
for role, n in [("BaseColor",0),("Normal",1),("ORM",2)]:
    stem = "T_WoodenTorch_"+role
    tex = lib.load_asset(folder+"/"+stem) if material_only else take(stem+".png",folder)
    if not material_only and role != "BaseColor":
        tex.set_editor_property("srgb",False)
        tex.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_NORMALMAP if role=="Normal" else u.TextureCompressionSettings.TC_MASKS)
    if not material_only and role=="Normal": tex.set_editor_property("flip_green_channel",True)
    node = edit.create_material_expression(mat,u.MaterialExpressionTextureSample,-400,n*240)
    node.texture = tex
    node.sampler_type = {"BaseColor":u.MaterialSamplerType.SAMPLERTYPE_COLOR,"Normal":u.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                         "ORM":u.MaterialSamplerType.SAMPLERTYPE_MASKS}[role]
    for channel, prop in {"BaseColor":[("RGB",u.MaterialProperty.MP_BASE_COLOR)],"Normal":[("RGB",u.MaterialProperty.MP_NORMAL)],
                          "ORM":[("G",u.MaterialProperty.MP_ROUGHNESS),("B",u.MaterialProperty.MP_METALLIC)]}[role]:
        pin = {u.MaterialProperty.MP_BASE_COLOR:"BaseColor",u.MaterialProperty.MP_ROUGHNESS:"Roughness",
               u.MaterialProperty.MP_METALLIC:"Metallic",u.MaterialProperty.MP_NORMAL:"Normal"}[prop]
        if not edit.connect_material_expressions(node,channel,slab,pin):
            raise RuntimeError("Material pin failed "+pin)
        edit.connect_material_property(node,channel,prop)
    results.append(tex)
if not edit.connect_material_property(slab,"",u.MaterialProperty.MP_FRONT_MATERIAL):
    raise RuntimeError("Failed to attach the torch surface")
edit.recompile_material(mat)
def save_remaining():
    if material_only:
        if not lib.save_loaded_asset(mat,False): raise RuntimeError("Save failed "+mat.get_path_name())
        (batch/"material-saved.json").write_text(json.dumps(mat.get_path_name()))
        return
    finish_item()

def finish_item():
    mesh.set_material(0,mat)
    x,y,z = json.loads((source/"fit.json").read_text())["flame_blender_cm"]
    for name,location in [("Flame",(x,-y,z)),("Grip",(0,0,0))]:
        sock = mesh.find_socket(name)
        if not sock:
            sock=u.new_object(u.StaticMeshSocket,outer=mesh)
            sock.set_editor_property("socket_name",name)
            mesh.add_socket(sock)
        sock.set_editor_property("relative_location",u.Vector(*location))
    icon=take("ue_wooden_torch.png",icons)
    icon.set_editor_property("lod_group",u.TextureGroup.TEXTUREGROUP_UI)
    icon.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_EDITOR_ICON)
    for obj in results+[mat,mesh,icon]:
        if not lib.save_loaded_asset(obj,False): raise RuntimeError("Save failed "+obj.get_path_name())
    (batch/"saved.json").write_text(json.dumps([o.get_path_name() for o in results+[mat,mesh,icon]],indent=2))


save_remaining()
