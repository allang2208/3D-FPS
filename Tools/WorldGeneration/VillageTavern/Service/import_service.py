"""Publish the isolated taproom service assets with their production material assignments."""
from pathlib import Path
import sys
import unreal as u

sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_kiln_textures import import_kiln_textures

source = Path(__file__).resolve().parents[4] / "SourceAssets/HillsVillageTavern/Service"
dest = "/Game/WorldGeneration/VillageTavern/Service"
assets = u.AssetToolsHelpers.get_asset_tools()
library = u.EditorAssetLibrary
editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
editing = u.MaterialEditingLibrary

def load(path):
    obj=u.load_asset(path)
    if not obj: raise RuntimeError("Missing " + path)
    return obj

def save(obj):
    if not library.save_loaded_asset(obj,False): raise RuntimeError("Could not save " + obj.get_path_name())

def task(name,ext):
    entry=u.AssetImportTask()
    entry.filename=str(source/(name+ext))
    entry.destination_path=dest
    entry.destination_name=name
    entry.automated=True
    entry.replace_existing=True
    return entry

textures=import_kiln_textures()

parent_name="M_TavernStoneware"
parent=library.load_asset(dest+"/"+parent_name) if library.does_asset_exist(dest+"/"+parent_name) else assets.create_asset(parent_name,dest,u.Material,u.MaterialFactoryNew())
parent.set_editor_property("used_with_instanced_static_meshes",True)
editing.delete_all_material_expressions(parent)
def node(cls,x,y):
    return editing.create_material_expression(parent,getattr(u,"MaterialExpression"+cls),x,y)
def link(a,out,b,pin):
    if not editing.connect_material_expressions(a,out,b,pin): raise RuntimeError("Material pin "+pin)
def output(expr,channel,prop):
    if not editing.connect_material_property(expr,channel,getattr(u.MaterialProperty,"MP_"+prop)): raise RuntimeError(prop)
def sample(suffix,typ,y):
    s=node("TextureSample",-680,y)
    s.texture=textures[suffix]
    s.sampler_type=getattr(u.MaterialSamplerType,"SAMPLERTYPE_"+typ)
    return s
alb=sample("Albedo","COLOR",-280)
mask=sample("Masks","MASKS",120)
normal=sample("Normal","NORMAL",450)
tint=node("VectorParameter",-680,-75)
tint.set_editor_property("parameter_name","SlipColor")
tint.set_editor_property("default_value",u.LinearColor(.24,.15,.08,1))
color=node("Multiply",-310,-150)
link(alb,"RGB",color,"A");link(tint,"",color,"B")
output(color,"","BASE_COLOR")
bare=node("ScalarParameter",-680,310)
bare.set_editor_property("parameter_name","BareClay")
rough=node("LinearInterpolate",-300,180)
link(mask,"G",rough,"A");link(mask,"B",rough,"B");link(bare,"",rough,"Alpha")
output(rough,"","ROUGHNESS");output(normal,"RGB","NORMAL");output(mask,"R","AMBIENT_OCCLUSION")
editing.recompile_material(parent)
save(parent)

mats={}
for slot,rgb,bare in (("Clay",(.32,.123,.058),1.),("OliveGlaze",(.114,.138,.066),.16),
                      ("HoneyGlaze",(.34,.151,.042),.12),("AshGlaze",(.53,.43,.29),.35)):
    name="MI_Tavern"+slot
    mi=load(dest+"/"+name) if library.does_asset_exist(dest+"/"+name) else assets.create_asset(name,dest,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    editing.set_material_instance_parent(mi,parent)
    editing.set_material_instance_vector_parameter_value(mi,"SlipColor",u.LinearColor(*rgb,1))
    editing.set_material_instance_scalar_parameter_value(mi,"BareClay",bare)
    editing.update_material_instance(mi)
    save(mi)
    mats[slot]=mi

timber="/Game/WorldGeneration/TemperateHills/"
mats["Oak"]=load(timber+"VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak")
mats["Iron"]=load(timber+"VillageCarpenter/Props/Surfaces/M_CarpenterIron")
mats["Endgrain"]=load(timber+"VillageCarpenter/Props/Surfaces/M_CarpenterCut")
for role in ("Tankard","Pitcher","Dish","Sherd","AleCask","TapCask"):
    name="SM_Tavern"+role
    entry=task(name,".fbx")
    opts=u.FbxImportUI()
    opts.import_mesh=True
    opts.import_as_skeletal=False
    opts.import_materials=False
    opts.import_textures=False
    opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data
    data.combine_meshes=True
    data.convert_scene=True
    data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True
    data.import_mesh_lods=True
    data.generate_lightmap_u_vs=True
    data.auto_generate_collision=role in ("AleCask","TapCask")
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    entry.options=opts
    entry.factory=u.FbxFactory()
    assets.import_asset_tasks([entry])
    mesh=load(dest+"/"+name)
    for i,slot in enumerate(mesh.static_materials):
        mesh.set_material(i,mats[str(slot.material_slot_name)])
    editor.set_lod_screen_sizes(mesh,[1.,.23,.065])
    save(mesh)
u.log("TAVERN_SERVICE_SAVED")
