"""Create/save M14 assets from produced files. Headless authoring, no game or render tests."""
from pathlib import Path
import json, traceback
import unreal as u
u.SystemLibrary.execute_console_command(None,"Interchange.FeatureFlags.Import.FBX 0")
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004")
OUT=ROOT/"ProductionV01"
DEST="/Game/Monsters/SpiralPillarM14"
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
REPORT=OUT/"Records/ue_delivery.json"
report=json.loads(REPORT.read_text(encoding="utf8")) if REPORT.exists() else {"saved":[],"stages":[],"tested":False,"rendered":False}
recipe=json.loads((OUT/"Records/production_recipe.json").read_text(encoding="utf8"))
def record():
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError("Save failed: "+asset.get_path_name())
    path=asset.get_path_name()
    if path not in report["saved"]:report["saved"].append(path)
    record()
def import_file(path,name,folder,options=None,factory=None):
    assetpath=folder+"/"+name
    if LIB.does_asset_exist(assetpath):return u.load_asset(assetpath)
    task=u.AssetImportTask();task.filename=str(path);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False
    if options:task.options=options
    if factory:task.factory=factory
    AT.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError("Import returned no assets: "+str(path))
    asset=u.load_asset(assetpath)
    if not asset:raise RuntimeError("Expected imported object missing: "+assetpath)
    return asset
def fbx(animation=False,skeleton=None):
    o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.import_as_skeletal=True
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_mesh=not animation;o.import_animations=animation;o.import_materials=False;o.import_textures=False
    if skeleton:o.skeleton=skeleton
    data=o.anim_sequence_import_data if animation else o.skeletal_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    if not animation:
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        o.create_physics_asset=True
    else:
        data.set_editor_property("use_default_sample_rate",False)
        data.set_editor_property("custom_sample_rate",30)
        data.set_editor_property("animation_length",u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    return o
def create_material(family,textures):
    name="M_M14_"+family;path=DEST+"/Materials/"+name
    if LIB.does_asset_exist(path):return u.load_asset(path)
    mat=AT.create_asset(name,DEST+"/Materials",u.Material,u.MaterialFactoryNew())
    mat.set_editor_property("two_sided",True)
    mat.set_editor_property("used_with_skeletal_mesh",True)
    slab=ME.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
    texnodes={}
    for key in ["BaseColor","Normal","MetallicRoughness"]:
        tex=ME.create_material_expression(mat,u.MaterialExpressionTextureSample)
        tex.texture=textures[key]
        tex.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=="BaseColor" else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=="Normal" else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        texnodes[key]=tex
    for key,channel,pin,prop in [
        ("BaseColor","RGB","BaseColor",u.MaterialProperty.MP_BASE_COLOR),
        ("Normal","RGB","Normal",u.MaterialProperty.MP_NORMAL),
        ("MetallicRoughness","G","Roughness",u.MaterialProperty.MP_ROUGHNESS),
        ("MetallicRoughness","B","Metallic",u.MaterialProperty.MP_METALLIC)]:
        if not ME.connect_material_expressions(texnodes[key],channel,slab,pin):raise RuntimeError("Material pin failed: "+pin)
        ME.connect_material_property(texnodes[key],channel,prop)
    if not ME.connect_material_property(slab,"",u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError("Substrate root not connected")
    errors=ME.recompile_material(mat)
    if errors:raise RuntimeError("Material compilation: "+str(errors))
    save(mat);return mat
def main():
    mesh=import_file(OUT/"Exports/M14_Skeletal_v01.fbx","SK_M14",DEST,fbx(),u.FbxFactory())
    for asset in [mesh,mesh.skeleton,mesh.physics_asset]:
        if asset:save(asset)
    if "mesh" not in report["stages"]:report["stages"].append("mesh");record()
    textures={}
    for key in ["BaseColor","MetallicRoughness","Normal"]:
        texture=import_file(ROOT/f"Textures/T_M14_{key}.jpg","T_M14_"+key,DEST+"/Textures")
        if key!="BaseColor":texture.set_editor_property("srgb",False)
        if key=="Normal":
            texture.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel",True)
        elif key=="MetallicRoughness":texture.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_MASKS)
        textures[key]=texture;save(texture)
    materials={family:create_material(family,textures) for family in ["Body","Mouth","Membrane","Metal"]}
    slots=list(mesh.materials)
    for slot in slots:
        name=str(slot.material_slot_name)
        family=next((key for key in materials if key.lower() in name.lower()),"Body")
        slot.material_interface=materials[family]
    mesh.set_editor_property("materials",slots);save(mesh)
    if "materials" not in report["stages"]:report["stages"].append("materials");record()
    clips={}
    for role,data in recipe["clips"].items():
        clip=import_file(data["file"],"A_M14_"+role,DEST+"/Animations",fbx(True,mesh.skeleton),u.FbxFactory())
        clip.set_editor_property("enable_root_motion",False);clip.set_editor_property("force_root_lock",True)
        clip.set_editor_property("loop",data["loop"]);clip.set_preview_skeletal_mesh(mesh);save(clip);clips[role]=clip
    save(mesh.skeleton)
    if "animations" not in report["stages"]:report["stages"].append("animations");record()
    if "physics" not in report["stages"]:
        if not u.SpiralPillarM14.build_physics(mesh,mesh.physics_asset):raise RuntimeError("M14 physics authoring failed")
        save(mesh.physics_asset);save(mesh)
        report["stages"].append("physics");record()
    bp_path=DEST+"/BP_SpiralPillarM14"
    if LIB.does_asset_exist(bp_path):bp=u.load_asset(bp_path)
    else:
        factory=u.BlueprintFactory();factory.set_editor_property("parent_class",u.SpiralPillarM14)
        bp=AT.create_asset("BP_SpiralPillarM14",DEST,u.Blueprint,factory)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property("visual_mesh",mesh)
    for prop,role in {"idle_clip":"Idle","move_clip":"Move","turn_left_clip":"TurnLeft","turn_right_clip":"TurnRight","bite_clip":"Bite","death_clip":"Death"}.items():
        cdo.set_editor_property(prop,clips[role])
    cdo.set_editor_property("bite_contact_seconds",recipe["bite_contact_seconds"])
    cdo.set_editor_property("walk_speed",recipe["animation_walk_speed_cm_s"])
    cdo.set_editor_property("animation_walk_speed",recipe["animation_walk_speed_cm_s"])
    ai=LIB.load_blueprint_class("/Game/Monsters/AI/BP_MonsterAIController")
    if not ai:raise RuntimeError("Existing shared monster AI blueprint is missing")
    cdo.set_editor_property("ai_controller_class",ai)
    combat=cdo.get_editor_property("combat");combat.set_editor_property("hit_clip",clips["Hit"])
    # Persist component template properties with the Blueprint package.
    cdo.get_editor_property("mesh").set_skeletal_mesh_asset(mesh)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    if "blueprint" not in report["stages"]:report["stages"].append("blueprint")
    report.update({"complete":True,"character":bp_path,"mesh":mesh.get_path_name(),
        "physics_bodies":len(mesh.physics_asset.get_editor_property("skeletal_body_setups")) if hasattr(mesh.physics_asset,"skeletal_body_setups") else "native authoring receipt",
        "f6_id":"SpiralPillarM14","height_cm":300,"source_triangles":recipe["source_triangles"],
        "bones":len(recipe["bones"]),"animation_count":len(clips),
        "source_polygon_reduction":False,"tests_run":False,"user_testing_pending":True})
    report.pop("error",None);record()
    print("M14_UE_ASSETS_SAVED "+str(len(report["saved"])))
try:main()
except Exception:
    report["complete"]=False;report["error"]=traceback.format_exc();record();raise
