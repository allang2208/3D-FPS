"""Publish the torch, its continuous near-field flame and the distant Niagara representation."""
import json
import os
import sys
from pathlib import Path
import unreal as u

root=Path(os.environ["FPS_PROJECT_ROOT"])
source=root/"SourceAssets/WoodenTorch20261122/HearthWrapR7"
out=source/"Export"
batch=Path(os.environ["TORCH_BATCH"])
family="/Game/Weapons/WoodenTorch20261122"
dest=family+"/HearthWrapR7"
lib=u.EditorAssetLibrary
edit=u.MaterialEditingLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
saved=[]
def save(obj):
    if not lib.save_loaded_asset(obj,False):raise RuntimeError("Cannot save "+obj.get_path_name())
    saved.append(obj.get_path_name())

def take(file,opt=None):
    task=u.AssetImportTask()
    task.filename=str(out/file);task.destination_path=dest;task.destination_name=Path(file).stem
    task.automated,task.replace_existing,task.save=True,True,False
    if opt:task.options=opt
    tools.import_asset_tasks([task])
    obj=lib.load_asset(dest+"/"+task.destination_name)
    if not obj:raise RuntimeError("Import failed: "+file)
    return obj

def material(name):
    m=lib.load_asset(dest+"/"+name) if lib.does_asset_exist(dest+"/"+name) else tools.create_asset(name,dest,u.Material,u.MaterialFactoryNew())
    edit.delete_all_material_expressions(m)
    return m
def node(m,cls,**props):
    n=edit.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(src,dst,pin="",channel=""):
    if not edit.connect_material_expressions(src,channel,dst,pin):raise RuntimeError(f"Cannot connect {dst.get_name()} {pin}")
def prop(n,p,ch=""):
    if not edit.connect_material_property(n,ch,p):raise RuntimeError("Cannot connect "+str(p))
def finish(mat):
    edit.layout_material_expressions(mat)
    edit.recompile_material(mat)
    save(mat)

mats={}
for part in ("Wood","Cloth","Rope","Leather"):
    m=material("M_Hearth"+part)
    masked=part=="Cloth"
    m.set_editor_property("two_sided",masked)
    m.set_editor_property("blend_mode",u.BlendMode.BLEND_MASKED if masked else u.BlendMode.BLEND_OPAQUE)
    slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    prefix=("/Game/Weapons/CommonHammerGrips20261014/BuildV1/Textures/T_HammerGrip_Leather_" if part=="Leather"
            else family+"/FabHandheldR2/T_HandheldTorch_"+part+"_")
    def texture(role,sampler):
        tex=lib.load_asset(prefix+role)
        if not tex:raise RuntimeError("Missing PBR input "+prefix+role)
        return node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler)
    base=texture("BaseColor",u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    nrm=texture("Normal",u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm=texture("ORM",u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    tinted=node(m,u.MaterialExpressionMultiply)
    link(base,tinted,"A","RGB");link(node(m,u.MaterialExpressionVertexColor),tinted,"B")
    link(tinted,slab,"BaseColor");link(nrm,slab,"Normal","RGB");link(orm,slab,"Roughness","G");link(orm,slab,"Metallic","B")
    prop(tinted,u.MaterialProperty.MP_BASE_COLOR);prop(nrm,u.MaterialProperty.MP_NORMAL,"RGB")
    prop(orm,u.MaterialProperty.MP_AMBIENT_OCCLUSION,"R");prop(orm,u.MaterialProperty.MP_ROUGHNESS,"G");prop(orm,u.MaterialProperty.MP_METALLIC,"B")
    if masked:prop(texture("Opacity",u.MaterialSamplerType.SAMPLERTYPE_MASKS),u.MaterialProperty.MP_OPACITY_MASK,"R")
    prop(slab,u.MaterialProperty.MP_FRONT_MATERIAL)
    finish(m);mats[part]=m

flow=take("T_HearthFlowVolume.png")
flow.set_editor_properties({"srgb":False,"compression_settings":u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,
                           "mip_gen_settings":u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                           "filter":u.TextureFilter.TF_BILINEAR,"never_stream":True})
save(flow)
fire=material("M_HearthFlameVolume")
fire.set_editor_properties({"blend_mode":u.BlendMode.BLEND_TRANSLUCENT,"shading_model":u.MaterialShadingModel.MSM_UNLIT,
                            "two_sided":False,"disable_depth_test":True,"allow_front_layer_translucency":False,
                            "output_translucent_velocity":False,"is_translucency_velocity_from_depth":False,
                            "translucency_pass":u.MaterialTranslucencyPass.MTP_BEFORE_DOF})
local=node(fire,u.MaterialExpressionLocalPosition)
eye=node(fire,u.MaterialExpressionTransformPosition,
         transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
         transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
link(node(fire,u.MaterialExpressionCameraPositionWS),eye)
up=node(fire,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
link(node(fire,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1)),up)
inputs={"LocalExit":local,"LocalEye":eye,"BehindDepth":node(fire,u.MaterialExpressionSceneDepth),
        "ExitDepth":node(fire,u.MaterialExpressionPixelDepth),"UpLocal":up,
        "TimeSeconds":node(fire,u.MaterialExpressionTime),
        "Phase":node(fire,u.MaterialExpressionScalarParameter,parameter_name="FlamePhase",
                     use_custom_primitive_data=True,primitive_data_index=0,default_value=0.),
        "FlowTex":node(fire,u.MaterialExpressionTextureObject,texture=flow,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)}
pins=[]
for key in inputs:
    pin=u.CustomInput();pin.set_editor_property("input_name",key);pins.append(pin)
field=node(fire,u.MaterialExpressionCustom,description="Head-wrapped fire, integrated to opaque depth",inputs=pins,
           output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,code=(source/"HearthVolume.hlsl").read_text("utf8"))
for k,p in inputs.items():link(p,field,k)
rgb=node(fire,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);link(field,rgb)
alpha=node(fire,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);link(field,alpha)
exposed=node(fire,u.MaterialExpressionEyeAdaptationInverse)
ep=[str(n) for n in edit.get_material_expression_input_names(exposed)]
link(rgb,exposed,ep[0]);link(node(fire,u.MaterialExpressionConstant,r=.52),exposed,ep[1])
slab=node(fire,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
link(exposed,slab,"Emissive Color");link(alpha,slab,"Opacity")
prop(exposed,u.MaterialProperty.MP_EMISSIVE_COLOR);prop(alpha,u.MaterialProperty.MP_OPACITY);prop(slab,u.MaterialProperty.MP_FRONT_MATERIAL)
finish(fire)

u.SystemLibrary.execute_console_command(None,"Interchange.FeatureFlags.Import.FBX 0")
opt=u.FbxImportUI()
opt.import_mesh=True;opt.import_as_skeletal=opt.import_materials=opt.import_textures=opt.import_animations=False
opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
mesh=take("SM_WrappedHearthTorch.fbx",opt)
slots=[]
for i,slot in enumerate(mesh.static_materials):
    name=str(slot.material_slot_name);mesh.set_material(i,mats[name]);slots.append(name)
if set(slots)!=set(mats):raise RuntimeError("Unexpected torch surfaces "+str(slots))
fit=json.loads((out/"fit.json").read_text())
for n,xyz in {"Grip":fit["grip_cm"],"Flame":fit["flame_cm"]}.items():
    sock=mesh.find_socket(n)
    if not sock:
        sock=u.new_object(u.StaticMeshSocket,outer=mesh);sock.set_editor_property("socket_name",n);mesh.add_socket(sock)
    sock.set_editor_property("relative_location",u.Vector(*xyz))
save(mesh)
volume=take("SM_HearthFlameVolume.fbx",opt)
volume.set_material(0,fire);save(volume)

sys.path.insert(0,str(root/"Tools/Skills"))
from build_fireball_assets import put,assignments,setdata,ref,emitters
target=dest+"/NS_HearthWrap"
system=lib.load_asset(target) if lib.does_asset_exist(target) else lib.duplicate_asset(family+"/HearthHeadR3/NS_HandheldHearth",target)
if set(emitters(system))!={"Fire","Smoke","Sparks"}:raise RuntimeError("Missing hearth emitter")
stage="ParticleSpawnScript"
v2="/Script/CoreUObject.Vector2f";v3="/Script/CoreUObject.Vector3f";pos="/Script/Niagara.NiagaraPosition"
up="float3(Engine.Owner.SystemXAxis.z,Engine.Owner.SystemYAxis.z,Engine.Owner.SystemZAxis.z)"
seed="frac(float(Particles.UniqueID)*.61803399)"
angle=f"(6.2831853*{seed})"
put(system,"Fire","EmitterUpdateScript","SpawnRate","SpawnRate","(Value=6.0)")
assignments(system,"Fire",stage,{"Particles.Position":(pos,f"float3(1.8*cos({angle}),1.8*sin({angle}),6.5)+{up}*5.0"),
                                "Particles.SpriteSize":(v2,f"float2(lerp(12.,15.,{seed}),lerp(22.,28.,{seed}))"),
                                "Particles.Velocity":(v3,f"{up}*5.0")})
assignments(system,"Smoke",stage,{"Particles.Position":(pos,f"float3(0,0,13.5)+{up}*8.0"),"Particles.Velocity":(v3,f"{up}*10.")})
assignments(system,"Sparks",stage,{"Particles.Position":(pos,f"float3(2.*cos({angle}),2.*sin({angle}),12.)"),
                                  "Particles.Velocity":(v3,f"{up}*lerp(11.,19.,{seed})+float3(cos({angle}),sin({angle}),0)")})
box={"min":dict(x=-28,y=-28,z=-16),"max":dict(x=28,y=28,z=53),"isValid":True}
for emitter in ("Fire","Smoke","Sparks"):
    setdata("SetEmitterData",u.NiagaraExt_EmitterData,ref(system,emitter),{"bLocalSpace":True,"CalculateBoundsMode":"Fixed","FixedBounds":box})
system.set_editor_property("fixed_bounds",u.Box(min=u.Vector(-28,-28,-16),max=u.Vector(28,28,53)))
if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError("Niagara compile failed")
save(system)
(batch/"assets-saved.json").write_text(json.dumps({"saved":saved,"mesh":mesh.get_path_name(),"mesh_height_cm":mesh.get_bounds().box_extent.z*2,
    "slots":slots,"fit":fit,"niagara_compiled":True,"proxy":volume.get_path_name()},indent=2),encoding="utf8")
