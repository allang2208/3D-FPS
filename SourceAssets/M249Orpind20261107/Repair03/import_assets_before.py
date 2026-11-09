"""Save the fitted skeletal mesh, workshop parts, game materials and native rig."""
from pathlib import Path
import json
import unreal as u

ROOT=Path(__file__).resolve().parent
DEST="/Game/Weapons/M249"
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
M=u.MaterialEditingLibrary
saved=[]
def existing(path):
    return E.load_asset(path) if E.does_asset_exist(path) else None
def save(o):
    if not o or not E.save_loaded_asset(o,False):raise RuntimeError("Save failed: "+str(o))
    saved.append(o.get_path_name())
def import_file(file,folder,name,options=None):
    t=u.AssetImportTask()
    t.filename=str(file);t.destination_path=folder;t.destination_name=name
    t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True
    if options:
        t.factory=u.FbxFactory();t.options=options
    A.import_asset_tasks([t])
    asset=existing(folder+"/"+name)
    if not asset:raise RuntimeError("Missing imported asset "+folder+"/"+name+" "+str(t.imported_object_paths))
    return asset
def new_mat(name):
    mat=existing(DEST+"/Materials/"+name)
    if mat:M.delete_all_material_expressions(mat)
    else:mat=A.create_asset(name,DEST+"/Materials",u.Material,u.MaterialFactoryNew())
    M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    return mat
def output(n,pin,prop):
    if not M.connect_material_property(n,pin,prop):raise RuntimeError("Material pin "+str(prop))
def connect(n,pin,to,key):
    if not M.connect_material_expressions(n,pin,to,key):raise RuntimeError(key)
def sample(mat,tex,sampler):
    n=M.create_material_expression(mat,u.MaterialExpressionTextureSample)
    n.texture=tex;n.sampler_type=sampler
    return n
def scalar(mat,num):
    n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.set_editor_property("r",num);return n
T=u.TextureCompressionSettings;ST=u.MaterialSamplerType;MP=u.MaterialProperty
textures={}
for f in sorted((ROOT/"Textures").glob("T_M249_*")):
    key=f.stem.split("_")[-1]
    tex=import_file(f,DEST+"/Textures",f.stem)
    tex.set_editor_property("srgb",key in ("Color","Emission"))
    if key=="Normal":
        tex.set_editor_property("compression_settings",T.TC_NORMALMAP)
        tex.set_editor_property("flip_green_channel",True)
    if key in ("ORM","Transmission"):tex.set_editor_property("compression_settings",T.TC_MASKS)
    if key=="Emission":tex.set_editor_property("max_texture_size",1024)
    save(tex);textures[key]=tex
surface=new_mat("M_M249_Surface")
surface.set_editor_property("blend_mode",u.BlendMode.BLEND_MASKED)
col=sample(surface,textures["Color"],ST.SAMPLERTYPE_COLOR)
output(col,"RGB",MP.MP_BASE_COLOR);output(col,"A",MP.MP_OPACITY_MASK)
orm=sample(surface,textures["ORM"],ST.SAMPLERTYPE_MASKS)
for pin,prop in (("R",MP.MP_AMBIENT_OCCLUSION),("G",MP.MP_ROUGHNESS),("B",MP.MP_METALLIC)):output(orm,pin,prop)
output(sample(surface,textures["Normal"],ST.SAMPLERTYPE_NORMAL),"RGB",MP.MP_NORMAL)
em=M.create_material_expression(surface,u.MaterialExpressionMultiply)
connect(scalar(surface,3.),"",em,"B")
connect(sample(surface,textures["Emission"],ST.SAMPLERTYPE_COLOR),"RGB",em,"A");output(em,"",MP.MP_EMISSIVE_COLOR)
M.recompile_material(surface);save(surface)
glass=new_mat("M_M249_Glass")
glass.set_editor_property("blend_mode",u.BlendMode.BLEND_TRANSLUCENT)
glass.set_editor_property("two_sided",True)
tint=M.create_material_expression(glass,u.MaterialExpressionConstant3Vector)
tint.set_editor_property("constant",u.LinearColor(.12,.23,.24,1))
output(tint,"",MP.MP_BASE_COLOR)
output(scalar(glass,.035),"",MP.MP_OPACITY)
output(scalar(glass,.11),"",MP.MP_ROUGHNESS)
M.recompile_material(glass);save(glass)

reticle=new_mat("M_M249_HoloReticle")
reticle.set_editor_property("shading_model",u.MaterialShadingModel.MSM_UNLIT)
reticle.set_editor_property("two_sided",True)
red=M.create_material_expression(reticle,u.MaterialExpressionConstant3Vector)
red.set_editor_property("constant",u.LinearColor(3.,.025,.01,1.))
output(red,"",MP.MP_EMISSIVE_COLOR)
M.recompile_material(reticle);save(reticle)
riser=new_mat("M_M249_Riser")
tone=M.create_material_expression(riser,u.MaterialExpressionConstant3Vector)
tone.set_editor_property("constant",u.LinearColor(.025,.03,.035,1))
output(tone,"",MP.MP_BASE_COLOR)
output(scalar(riser,.75),"",MP.MP_METALLIC)
output(scalar(riser,.42),"",MP.MP_ROUGHNESS)
M.recompile_material(riser);save(riser)

donor=E.load_asset("/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular")
skel=existing(DEST+"/SK_M249_Skeleton") or E.duplicate_asset(donor.skeleton.get_path_name(),DEST+"/SK_M249_Skeleton")
if not skel:raise RuntimeError("Private M249 skeleton creation failed")
skinmesh=E.load_asset("/Game/Characters/ModularOutfit20260924/BarePalmV7/PKM/SK_PKM_BareArmsV7")
skin={str(s.material_slot_name):s.material_interface for s in skinmesh.materials}
def material(name):
    if name in skin:return skin[name]
    if name.startswith("Skin_"):
        names=["Skin_UpperArm","Skin_Forearm","Skin_Hand"]
        return skinmesh.materials[names.index(name)].material_interface
    if name in ("M249_Glass","M249_HoloGlass","M249_MagnifierGlass"):return glass
    if name=="M249_HoloReticle":return reticle
    if name=="M249_Riser":return riser
    if name.startswith("M249_"):return surface
    if name.startswith("Feed"):
        base="CaseLacquer" if name.startswith("FeedCase") else "CopperJacket" if name.startswith("FeedCopper") else "BluedSteel"
        return E.load_asset("/Game/Weapons/PKMLowpoly20260922/Materials/M_PKM_"+base)
    raise RuntimeError("Unknown M249 FBX slot "+name)

flag="Interchange.FeatureFlags.Import.FBX"
old=u.SystemLibrary.get_console_variable_int_value(flag)
report={"static":[]}
try:
    u.SystemLibrary.execute_console_command(None,flag+" 0")
    for f in sorted((ROOT/"Exports").glob("*.fbx")):
        skeletal=f.stem=="SK_M249_V7"
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
        opt.import_animations=False;opt.create_physics_asset=False
        if skeletal:
            opt.skeleton=skel
            data=opt.skeletal_mesh_import_data
            data.set_editor_property("update_skeleton_reference_pose",False)
            data.set_editor_property("use_t0_as_ref_pose",False)
        else:
            data=opt.static_mesh_import_data
            data.set_editor_property("combine_meshes",True)
            data.set_editor_property("auto_generate_collision",False)
        data.set_editor_property("normal_import_method",u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        mesh=import_file(f,DEST if skeletal else DEST+"/Assembly",f.stem,opt)
        prop="materials" if skeletal else "static_materials"
        slots=mesh.get_editor_property(prop);hide=[]
        for i,slot in enumerate(slots):
            name=str(slot.material_slot_name)
            slot.material_interface=material(name)
            slots[i]=slot
            if name.startswith("Skin_"):hide.append(i)
        mesh.set_editor_property(prop,slots);save(mesh)
        if skeletal:
            report.update(mesh=mesh.get_path_name(),skin_slots=hide,skeleton=mesh.skeleton.get_path_name())
            u.AnimationLibrary.set_skeleton_preview_mesh(skel,mesh,True)
            save(skel)
        else:report["static"].append(mesh.get_path_name())
finally:u.SystemLibrary.execute_console_command(None,flag+" "+str(old))
report["saved"]=saved
(ROOT/"assets_saved.json").write_text(json.dumps(report,indent=2),encoding="utf8")
print("M249_ASSETS_SAVED",len(saved),flush=True)
