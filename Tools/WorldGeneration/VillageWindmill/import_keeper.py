"""Import the skinned keeper, her private idle and her replicated village actor."""
import json
import sys
from pathlib import Path
import unreal as u
sys.path.insert(0, str(Path(__file__).resolve().parent))
from keeper_fabrics import material_paths, save_fabrics

PROJECT=Path(__file__).resolve().parents[3]
ROOT=PROJECT/"SourceAssets/HillsVillageWindmill/MillKeeper/CharacterR1/Assembly"
DEST="/Game/WorldGeneration/TemperateHills/AbandonedVillage/MillKeeper"
spec=json.loads((ROOT/"assembly.json").read_text())
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools(); L=u.MaterialEditingLibrary

def save(obj):
    if not obj or not obj.get_path_name().startswith(DEST+"/") or not E.save_loaded_asset(obj,False):
        raise RuntimeError("Could not save keeper package "+str(obj))
    return obj

def face_material(name, maps):
    path=DEST+"/M_"+name
    mat=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset("M_"+name,DEST,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
    for i,(kind,file) in enumerate(maps.items()):
        task=u.AssetImportTask();task.filename=str(ROOT/file);task.destination_path=DEST+"/Textures"
        task.automated=True;task.replace_existing=True;task.factory=u.TextureFactory();A.import_asset_tasks([task])
        tex=task.get_objects()[0]
        normal=kind=="N"; color=kind=="BC"
        tex.srgb=color
        tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else (u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS)
        if normal:tex.flip_green_channel=True
        save(tex)
        s=L.create_material_expression(mat,u.MaterialExpressionTextureSample,-400,200*i);s.texture=tex
        s.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else (u.MaterialSamplerType.SAMPLERTYPE_COLOR if color else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        if not L.connect_material_expressions(s,"RGB" if normal or color else "R",slab,
                    {"N":"Normal","R":"Roughness","M":"Metallic","BC":"BaseColor"}[kind]):raise RuntimeError(kind)
    L.connect_material_property(slab,"",u.MaterialProperty.MP_FRONT_MATERIAL);L.recompile_material(mat)
    return save(mat)


def save_base(skeleton, mats):
    task=u.AssetImportTask();task.filename=str(ROOT/"SK_MillKeeper_Base.fbx");task.destination_path=DEST
    task.automated=True;task.replace_existing=True;task.factory=u.FbxFactory()
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opts.import_as_skeletal=True;opts.import_mesh=True
    opts.skeleton=skeleton;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False
    opts.skeletal_mesh_import_data.convert_scene=False;opts.skeletal_mesh_import_data.convert_scene_unit=True
    task.options=opts;A.import_asset_tasks([task])
    base=next(obj for obj in task.get_objects() if isinstance(obj,u.SkeletalMesh))
    slots=list(base.materials)
    for slot in slots:slot.material_interface=mats[str(slot.material_slot_name)]
    base.materials=slots
    return save(base)

def main():
    save_fabrics()
    spec["materials"].update(material_paths())
    receipt=ROOT/"saved.json"
    if receipt.is_file():
        previous=json.loads(receipt.read_text())
        if "base" not in previous and E.does_asset_exist(previous["character"]):
            mesh=E.load_asset(previous["mesh"])
            mats={key:E.load_asset(spec["materials"][key]) for key in ("Hands","WorkLinen","Skirt")}
            base=save_base(mesh.skeleton,mats)
            previous.update(base=base.get_path_name(),packages=list(E.list_assets(DEST,True,False)))
            receipt.write_text(json.dumps(previous,indent=2))
            return
    mats={name:(face_material(name,src) if isinstance(src,dict) else E.load_asset(src))
          for name,src in spec["materials"].items()}
    if not all(mats.values()):raise RuntimeError("Missing keeper wardrobe material")
    task=u.AssetImportTask();task.filename=str(ROOT/"SK_MillKeeper.fbx");task.destination_path=DEST
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.FbxFactory()
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opts.import_mesh=True;opts.import_as_skeletal=True;opts.import_animations=True
    opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False
    opts.override_animation_name="A_MillKeeper_Idle"
    sk=opts.skeletal_mesh_import_data;sk.convert_scene=False;sk.convert_scene_unit=True
    sk.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    opts.anim_sequence_import_data.convert_scene=False;opts.anim_sequence_import_data.convert_scene_unit=True
    task.options=opts;A.import_asset_tasks([task])
    assets=task.get_objects()
    mesh=next(x for x in assets if isinstance(x,u.SkeletalMesh))
    idle=E.load_asset(DEST+"/A_MillKeeper_Idle")
    if not isinstance(idle,u.AnimSequence): raise RuntimeError("Missing imported keeper idle")
    slots=list(mesh.materials)
    for slot in slots:
        name=str(slot.material_slot_name)
        slot.material_interface=mats[name]
    mesh.materials=slots
    policy=E.load_asset("/Game/Characters/VillageBaker/DA_BakerLOD")
    if policy:
        mesh.set_editor_property("lod_settings",policy)
        u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh,4,True,False)
    for x in (mesh.skeleton,mesh,idle):save(x)
    base=save_base(mesh.skeleton,mats)
    bp = save_keeper_blueprint(mesh, idle)
    files=[p for p in E.list_assets(DEST,True,False) if p.startswith(DEST+"/")]
    (ROOT/"saved.json").write_text(json.dumps(dict(mesh=mesh.get_path_name(),base=base.get_path_name(),idle=idle.get_path_name(),
        character=bp.get_path_name(),packages=files,runtime_tested=False),indent=2))


def save_keeper_blueprint(mesh, idle):
    path = DEST + "/BP_MillKeeper"
    if E.does_asset_exist(path):
        bp = E.load_asset(path)
        if not isinstance(u.get_default_object(bp.generated_class()), u.VillageMillKeeper):
            u.BlueprintEditorLibrary.reparent_blueprint(bp, u.VillageMillKeeper)
    else:
        factory = u.BlueprintFactory()
        factory.set_editor_property("parent_class", u.VillageMillKeeper)
        bp = A.create_asset("BP_MillKeeper", DEST, u.Blueprint, factory)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    if not isinstance(cdo, u.VillageMillKeeper):
        raise RuntimeError("Could not bind the mill keeper's resident class")
    cdo.modify();cdo.set_editor_property("replicates",True)
    cdo.set_editor_property("auto_possess_ai",u.AutoPossessAI.DISABLED)
    cdo.set_editor_property("tags",["NPC","Friendly","VillageMillKeeper"])
    cap=cdo.get_editor_property("capsule_component");cap.modify();cap.set_capsule_size(23.,77.5,False)
    body=cdo.get_editor_property("mesh");body.modify();body.set_skeletal_mesh_asset(mesh)
    body.set_relative_location(u.Vector(0,0,-77.5),False,False)
    body.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
    data=body.get_editor_property("animation_data");data.anim_to_play=idle;data.saved_looping=True
    data.saved_playing=True;body.set_editor_property("animation_data",data)
    move=cdo.get_editor_property("character_movement");move.set_editor_property("default_land_movement_mode",u.MovementMode.MOVE_NONE)
    return save(bp)


if __name__ == "__main__":
    main()
