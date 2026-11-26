"""Write the two new R4 skeletal parts and their owned surface assets via a background UE commandlet."""
import gzip
import json
import os
from pathlib import Path
import unreal as u

root=Path(__file__).resolve().parents[3]
src=root/"SourceAssets/HillsVillageHighWall20261120/MasterArtisan"
dest="/Game/Characters/VillageMasterArtisan"
revision=globals().get("head_revision",os.getenv("MASTER_ARTISAN_HEAD_REVISION","R1"))
head_pass=revision in ("R2","R3","R4")
workwear_pass=revision in ("WorkwearR5","WorkwearR6")
surface_dest=dest
if head_pass:
    src=src/("Head"+revision)
    surface_dest=dest+"/Head"+revision
elif workwear_pass:
    src=src/revision
    surface_dest=dest+"/"+revision
smith="/Game/Characters/VillageBlacksmithNPC20261118"
lib=u.EditorAssetLibrary
assets=u.AssetToolsHelpers.get_asset_tools()
materials=u.MaterialEditingLibrary
prop=u.MaterialProperty
written=[]

def save(obj):
    if not obj or not obj.get_path_name().startswith(dest+"/") or not lib.save_loaded_asset(obj,False):
        raise RuntimeError("Failed to save "+str(obj))
    written.append(obj.get_path_name().split(".")[0])
    return obj

def require(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError("Missing authoring dependency "+path)
    return obj

def texture(name):
    label="T_Artisan"+name
    job=u.AssetImportTask()
    job.filename=str(src/(label+".png"))
    job.destination_path=surface_dest+"/Textures"
    job.destination_name=label
    job.automated=True
    job.replace_existing=True
    job.save=False
    assets.import_asset_tasks([job])
    tex=require(job.destination_path+"/"+label)
    if name=="HeadDetail":
        tex.set_editor_property("srgb",False)
        tex.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_NORMALMAP)
        if revision=="R4":tex.set_editor_property("flip_green_channel",True)
        tex.set_editor_property("lod_group",u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP)
    elif name=="HeadORM":
        tex.set_editor_property("srgb",False)
        tex.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("lod_group",u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)
    else:
        tex.set_editor_property("lod_group",u.TextureGroup.TEXTUREGROUP_CHARACTER)
    return save(tex)

def shader(name):
    slot="M_Artisan"+name
    folder=surface_dest+"/Materials"
    obj=lib.load_asset(folder+"/"+slot) if lib.does_asset_exist(folder+"/"+slot) else assets.create_asset(slot,folder,u.Material,u.MaterialFactoryNew())
    materials.delete_all_material_expressions(obj)
    materials.set_material_usage(obj,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    def node(cls,**properties):
        n=materials.create_material_expression(obj,cls)
        for key,val in properties.items(): n.set_editor_property(key,val)
        return n
    def wire(n,channel,pin):
        if not materials.connect_material_property(n,channel,pin):raise RuntimeError("Material input "+str(pin))
    def scalar(val,pin):
        wire(node(u.MaterialExpressionConstant,r=val),"",pin)
    def sample(tex,sampler):
        return node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler)
    if name in ("Head","Neck","Hair","Indigo","Lapel","Flax"):
        wire(sample(texture(name),u.MaterialSamplerType.SAMPLERTYPE_COLOR),"RGB",prop.MP_BASE_COLOR)
        if name in ("Head","Neck"):
            detail=texture("HeadDetail") if name=="Head" and revision in ("R2","R4") else require("/Game/AsianMale_Jason/Texture/T_Head_LOD2_N")
            wire(sample(detail,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),"RGB",prop.MP_NORMAL)
            if revision=="R4" and name=="Head":
                orm=sample(texture("HeadORM"),u.MaterialSamplerType.SAMPLERTYPE_MASKS)
                wire(orm,"R",prop.MP_AMBIENT_OCCLUSION)
                wire(orm,"G",prop.MP_ROUGHNESS)
                wire(orm,"B",prop.MP_METALLIC)
            else:scalar(.54,prop.MP_ROUGHNESS)
        elif name=="Hair":
            scalar(.51,prop.MP_ROUGHNESS)
        else:
            path=smith+"/BodyOutfit/SurfaceR2/T_Smith_Linen_"
            wire(sample(require(path+"N"),u.MaterialSamplerType.SAMPLERTYPE_NORMAL),"RGB",prop.MP_NORMAL)
            orm=sample(require(path+"ORM"),u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            wire(orm,"G",prop.MP_ROUGHNESS)
            wire(orm,"R",prop.MP_AMBIENT_OCCLUSION)
            obj.set_editor_property("two_sided",True)
    else:
        rgb,rough,metal={"Frame":((.020,.015,.011),.26,.10),"Lens":((.78,.86,.89),.06,0),
                         "Iron":((.14,.15,.16),.41,.85),"Toolwood":((.29,.14,.049),.50,0),
                         "WaxThread":((.16,.092,.045),.80,0)}[name]
        if name=="Lens":
            obj.set_editor_property("blend_mode",u.BlendMode.BLEND_TRANSLUCENT)
            obj.set_editor_property("two_sided",True)
            obj.set_editor_property("translucency_lighting_mode",u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
            scalar(.055,prop.MP_OPACITY)
        wire(node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*rgb,1)),"",prop.MP_BASE_COLOR)
        scalar(rough,prop.MP_ROUGHNESS)
        scalar(metal,prop.MP_METALLIC)
    materials.recompile_material(obj)
    return save(obj)

def leather_finish(name):
    label="M_Artisan"+name
    folder=surface_dest+"/Materials"
    path=folder+"/"+label
    if lib.does_asset_exist(path):return require(path)
    m=assets.duplicate_asset(label,folder,require(smith+"/BodyOutfit/Materials/M_Smith_"+name))
    previous=materials.get_material_property_input_node(m,prop.MP_ROUGHNESS)
    channel=materials.get_material_property_input_node_output_name(m,prop.MP_ROUGHNESS)
    remap=materials.create_material_expression(m,u.MaterialExpressionLinearInterpolate)
    remap.set_editor_property("const_a",.48 if name=="Apron" else .41)
    remap.set_editor_property("const_b",.90 if name=="Apron" else .86)
    if not materials.connect_material_expressions(previous,channel,remap,"Alpha"):raise RuntimeError("Leather roughness input")
    if not materials.connect_material_property(remap,"",prop.MP_ROUGHNESS):raise RuntimeError("Leather roughness output")
    spec=materials.create_material_expression(m,u.MaterialExpressionConstant)
    spec.set_editor_property("r",.30 if name=="Apron" else .35)
    materials.connect_material_property(spec,"",prop.MP_SPECULAR)
    materials.recompile_material(m)
    return save(m)

material_cache={}
def resolve(name):
    if name not in material_cache:
        if name.startswith("/Game/"):m=require(name)
        elif revision=="R3" and name in ("Frame","Hair","Indigo","Lens"):
            m=require(dest+"/Materials/M_Artisan"+name)
        elif revision=="R3" and name=="Brass":m=require(smith+"/BodyOutfit/Materials/M_Smith_Brass")
        elif revision=="WorkwearR6" and name in ("Apron","Saddle"):
            m=leather_finish(name)
        elif revision=="WorkwearR6" and name in ("Flax","WaxThread"):
            m=require(dest+"/WorkwearR5/Materials/M_Artisan"+name)
        elif workwear_pass and name in ("Indigo","Lapel","Toolwood","Iron"):
            m=require(dest+"/Materials/M_Artisan"+name)
        elif name in ("Twill","Apron","Saddle","Boot","Sole","Brass","Thread"):
            m=require(smith+"/BodyOutfit/Materials/M_Smith_"+name)
        elif globals().get("use_published_surfaces",False):m=require(surface_dest+"/Materials/M_Artisan"+name)
        else:m=shader(name)
        material_cache[name]=m
    return material_cache[name]

geo=u.GeometryScript_AssetUtils
bind=u.GeometryScript_BoneWeights
body=require(smith+"/SK_Smith_Body")
ref,status=geo.copy_mesh_from_skeletal_mesh(body,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("R4 body reference pose unavailable")
for name in (("Head",) if head_pass else ("Workwear",) if workwear_pass else ("Head","Workwear")):
    with gzip.open(src/(name+".json.gz"),"rt",encoding="utf8") as f:model=json.load(f)
    dm=u.DynamicMesh()
    mats=[resolve(x) for x in model["materials"]]
    buffers=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*p) for p in model["p"]],
        normals=[u.Vector(*v) for v in model["n"]],uv0=[u.Vector2D(*uv) for uv in model["uv"]],
        triangles=[u.IntVector(*tri) for tri in model["tri"]])
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buffers,0,True)
    bind.copy_bones_from_mesh(ref,dm)
    bind.mesh_create_bone_weights(dm)
    for i,row in enumerate(model["w"]):
        bind.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=k,weight=w) for k,w in row])
    ids=u.GeometryScript_List.convert_array_to_index_list(model["m"],u.GeometryScriptIndexType.MATERIAL_ID)
    setter=next(getattr(u.GeometryScript_Materials,k) for k in dir(u.GeometryScript_Materials) if k.replace("_","").lower()=="setalltrianglematerialids")
    setter(dm,ids,True)
    path=dest+"/SK_MasterArtisan_"+name
    opts=u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    opts.use_mesh_bone_proportions=True
    opts.enable_recompute_normals=False
    opts.enable_recompute_tangents=True
    names=["Section_"+str(i)+"_"+s.split("/")[-1] for i,s in enumerate(model["materials"])]
    opts.materials=dict(zip(names,mats))
    if lib.does_asset_exist(path):
        obj=require(path)
        copy=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=names,
            enable_recompute_normals=False,enable_recompute_tangents=True)
        _,status=geo.copy_mesh_to_skeletal_mesh(dm,obj,copy,u.GeometryScriptMeshWriteLOD(lod_index=0))
    else:
        obj,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,body.skeleton,path,opts)
    if status!=u.GeometryScriptOutcomePins.SUCCESS or not obj:raise RuntimeError("Could not write "+path)
    if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(obj,3,True,False):raise RuntimeError("LOD build "+path)
    save(obj)
    print("ARTISAN_SAVED "+path,flush=True)
if not globals().get("use_published_surfaces",False):
    (src/"saved.json").write_text(json.dumps({"packages":written,"skeleton":body.skeleton.get_path_name(),"body":body.get_path_name()},indent=2))
