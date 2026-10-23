"""Save authored sources; preserve the harness and sewn bag seams in LOD1.

Optional checks are user-requested work, not a prerequisite for ordinary asset
authoring. A manifest digest, when supplied, binds this save to its source.
"""
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
import unreal as u

P=Path("D:/FPS3D/FPSGAME")
R=P/"SourceAssets/BackpackHarnessRebuild20261020"
DEST="/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003"
E,G=u.EditorAssetLibrary,u.GeometryScript_AssetUtils
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
manifest=json.loads((R/"manifest.json").read_text())
shell_only=manifest.get("save_scope")=="shell_only"
for row in manifest["variants"]:
    digest=hashlib.sha256(Path(row["source"]).read_bytes()).hexdigest()
    if row.get("source_sha256") and digest!=row["source_sha256"]:
        raise RuntimeError("Source changed after authoring: "+row["profile"])
if "-run=" not in u.SystemLibrary.get_command_line().lower():
    if u.EditorLevelLibrary.get_pie_worlds(False):
        raise RuntimeError("End PIE before replacing backpack assets")
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    targets={row["asset"].split(".")[0] for row in manifest["variants"]}
    targets.update(DEST+'/'+name for name in ('M_BackpackHarness_FabricR1','M_BackpackHarness_Hardware'))
    for prefix in ('T_HarnessFabricR1_','T_BackpackHardware_'):
        targets.update(DEST+'/Textures/'+prefix+channel for channel in ('BaseColor','ORM','Normal'))
    if targets & dirty:
        raise RuntimeError("A target backpack or material has unsaved editor edits")
spec=importlib.util.spec_from_file_location("harness_dynamic_io",P/"Tools/ChainmailPants/save_assets.py")
io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
spec=importlib.util.spec_from_file_location("backpack_winding",P/"Tools/BackpackHarness/winding.py")
winding=importlib.util.module_from_spec(spec);spec.loader.exec_module(winding)


def dynamic(data,native):
    return io.dynamic(winding.to_unreal(data),native)


def correct_simplified_normals(mesh):
    """Repair only reduced bag faces whose retained normals oppose their face."""
    Q=u.GeometryScript_MeshQueries
    repaired=0
    for ti in range(mesh.get_triangle_count()):
        valid,a,b,c=Q.get_triangle_positions(mesh,ti)
        _,na,nb,nc,nvalid=Q.get_triangle_normals(mesh,ti)
        if not valid or not nvalid:raise RuntimeError("Missing reduced bag face attributes")
        e1,e2=b-a,c-a
        n=u.Vector(e2.y*e1.z-e2.z*e1.y,e2.z*e1.x-e2.x*e1.z,e2.x*e1.y-e2.y*e1.x)
        length=(n.x*n.x+n.y*n.y+n.z*n.z)**.5
        if length<=1e-8:continue
        n=n/length
        mean=(na+nb+nc)/3.
        if n.x*mean.x+n.y*mean.y+n.z*mean.z < 0.:
            u.GeometryScript_Normals.set_mesh_triangle_normals(mesh,ti,
                u.GeometryScriptTriangle(vector0=n,vector1=n,vector2=n),True)
            repaired+=1
    return repaired


def save(asset):
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):
        raise RuntimeError("Save failed: "+asset.get_path_name())


def textured_material(hardware=False):
    L=u.MaterialEditingLibrary
    folder=DEST+"/Textures";E.make_directory(folder)
    name='M_BackpackHarness_Hardware' if hardware else 'M_BackpackHarness_FabricR1'
    path=DEST+'/'+name
    mat=u.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset(
        name,DEST,u.Material,u.MaterialFactoryNew())
    textures={}
    for channel in ("BaseColor","ORM","Normal"):
        suffix="_GL" if channel=="Normal" else ""
        task=u.AssetImportTask()
        task.filename=str(R/('HardwareInputs' if hardware else 'Textures')/
                          (('T_BackpackHardware_' if hardware else 'T_HarnessFabric_')+channel+suffix+'.png'))
        task.destination_path=folder;task.destination_name=('T_BackpackHardware_' if hardware else 'T_HarnessFabricR1_')+channel
        task.automated=True;task.replace_existing=True;task.save=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture=u.load_asset(folder+"/"+task.destination_name)
        if not texture:raise RuntimeError("Fabric texture import failed")
        texture.set_editor_property("srgb",channel=="BaseColor")
        texture.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_NORMALMAP if channel=="Normal"
                                    else u.TextureCompressionSettings.TC_MASKS if channel=="ORM" else u.TextureCompressionSettings.TC_DEFAULT)
        texture.set_editor_property("never_stream",False);texture.set_editor_property("max_texture_size",1024)
        texture.set_editor_property("address_x",u.TextureAddress.TA_WRAP);texture.set_editor_property("address_y",u.TextureAddress.TA_WRAP)
        if channel=="Normal":texture.set_editor_property("flip_green_channel",True)
        save(texture);textures[channel]=texture
    L.delete_all_material_expressions(mat)
    for channel,texture in textures.items():
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
        node.set_editor_property("parameter_name",channel);node.set_editor_property("texture",texture)
        node.set_editor_property("sampler_type",u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=="Normal"
                                else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=="ORM" else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        outputs=[("RGB",u.MaterialProperty.MP_BASE_COLOR)] if channel=="BaseColor" else [("RGB",u.MaterialProperty.MP_NORMAL)] if channel=="Normal" else [
            ("R",u.MaterialProperty.MP_AMBIENT_OCCLUSION),("G",u.MaterialProperty.MP_ROUGHNESS),("B",u.MaterialProperty.MP_METALLIC)]
        for pin,prop in outputs:
            if not L.connect_material_property(node,pin,prop):raise RuntimeError("Fabric material connection failed")
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    mat.set_editor_property("two_sided",False)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError("Fabric material compile failed: "+str(errors))
    save(mat)
    return mat.get_path_name()


fabric=DEST+'/M_BackpackHarness_FabricR1.M_BackpackHarness_FabricR1' if shell_only else textured_material()
hardware=DEST+'/M_BackpackHarness_Hardware.M_BackpackHarness_Hardware' if shell_only else textured_material(True)
receipts={}
receipt_path=R/"saved_assets.json"
if receipt_path.exists():receipts=json.loads(receipt_path.read_text())
for row in manifest["variants"]:
    profile=row["profile"];source=Path(row["source"]);digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if (receipts.get(profile,{}).get("sha256")==digest and receipts[profile].get("saved")
            and receipts[profile].get("ue_front_face_convention")==winding.UE_CONVENTION
            and receipts[profile].get("lod1_normal_policy")=="correct_opposed_reduced_faces"):
        print("HARNESS_SAVE_RESUMED",profile,flush=True);continue
    data=json.loads(source.read_text())
    path=row["asset"].split(".")[0]
    asset=u.load_asset(path)
    if not asset:
        asset=E.duplicate_asset(DEST+"/SK_Jason_Backpack",path)
    if not asset:raise RuntimeError("Cannot load/create "+path)
    disk=P/"Content"/(path.removeprefix("/Game/")+".uasset")
    backup=R/"Before/Content"/disk.relative_to(P/"Content")
    if disk.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    native,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Cannot read native skeleton")
    dm=dynamic(data,native)
    materials=[u.load_asset(m["asset"]) for m in data["materials"]]
    if any(m is None for m in materials):raise RuntimeError("Missing harness material")
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,
        new_material_slot_names=[m["slot"] for m in data["materials"]],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD(lod_index=0))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Cannot write harness LOD0")
    setting=S.get_lod_build_settings(asset,0);setting.set_editor_property("use_full_precision_u_vs",True)
    S.set_lod_build_settings(asset,0,setting)
    nf=data["harness_face_count"]
    def subset(start,end):
        out=dict(data)
        for field in ("triangles","uv","normals","triangle_materials"):out[field]=data[field][start:end]
        return dynamic(out,native)
    cap_count=data.get("bag_cap_face_count",0)
    bag=subset(nf,None);harness=subset(0,nf)
    # The import helper splits geometric vertices at UV/normal seams. Reducing
    # those islands independently opens cracks. Join only coincident boundary
    # pairs on the rigid bag; retain the separate UV/normal overlay elements.
    u.GeometryScript_MeshRepair.weld_mesh_edges(bag,
        u.GeometryScriptWeldEdgesOptions(tolerance=.0001,only_unique_pairs=True))
    simplify=u.GeometryScriptSimplifyMeshOptions(allow_seam_splits=False,allow_seam_smoothing=False,
        allow_seam_collapse=False,preserve_vertex_positions=True)
    u.GeometryScript_MeshSimplification.apply_simplify_to_triangle_count(bag,int(bag.get_triangle_count()*.48),simplify,None)
    repaired_normals=correct_simplified_normals(bag)
    u.GeometryScript_MeshEdits.append_mesh(bag,harness,u.Transform(),True)
    _,status=G.copy_mesh_to_skeletal_mesh(bag,asset,
        u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),
        u.GeometryScriptMeshWriteLOD(lod_index=1))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Cannot write harness LOD1")
    E.set_metadata_tag(asset,"BackpackHarnessRevision",manifest["revision"])
    E.set_metadata_tag(asset,"BackpackHarnessSource",str(source))
    E.set_metadata_tag(asset,"BackpackHarnessSourceSHA256",digest)
    E.set_metadata_tag(asset,"BackpackHarnessContract",data["contract"])
    E.set_metadata_tag(asset,"BackpackFrontFaceConvention",winding.UE_CONVENTION)
    save(asset)
    receipts[profile]={"asset":asset.get_path_name(),"sha256":digest,"saved":True,"revision":manifest["revision"],
                       "lod0_triangles":dm.get_triangle_count(),"lod1_triangles":bag.get_triangle_count(),
                       "harness_lod1_preserved":harness.get_triangle_count(),"fabric":fabric,
                       "bag_closure_source_faces":cap_count,"lod1_seam_collapse":False,
                       "ue_front_face_convention":winding.UE_CONVENTION,
                       "lod1_normal_policy":"correct_opposed_reduced_faces","lod1_corrected_normal_faces":repaired_normals,
                       "accepted_by_user":False}
    receipt_path.write_text(json.dumps(receipts,indent=2),encoding="utf-8")
    print("HARNESS_SAVED",json.dumps(receipts[profile]),flush=True)
    del dm,native,bag,harness,data
    u.SystemLibrary.collect_garbage()
print("HARNESS_SAVE_COMPLETE",len(receipts),flush=True)
