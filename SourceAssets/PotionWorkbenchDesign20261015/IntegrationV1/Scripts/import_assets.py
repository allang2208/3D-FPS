"""Import only this workbench's new packages in the isolated headless host."""
from pathlib import Path
import json,re,unreal as u
ROOT=Path(__file__).resolve().parents[1]
DEST="/Game/Building/PotionWorkbench20261015/V1"
OWNER="PotionWorkbench20261015_IntegrationV1"
SPEC=json.loads((ROOT/"buildable_manifest.json").read_text("utf8"))
if Path(u.Paths.project_dir()).resolve()!=(ROOT/"UEImportHost").resolve():
    raise RuntimeError("Use the isolated potion workbench import host")
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report={"stage":"importing","textures":[],"materials":[],"mesh":None,"runtime_tested":False}
def receipt():
    (ROOT/"Receipts/ue-import.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")
def save(obj):
    obj.modify();E.set_metadata_tag(obj,"PotionWorkbench.Owner",OWNER)
    if not E.save_loaded_asset(obj,False):raise RuntimeError("Asset save failed "+obj.get_path_name())
def imp(source,name,folder,options=None):
    path=folder+"/"+name
    if E.does_asset_exist(path):
        obj=u.load_asset(path)
        if E.get_metadata_tag(obj,"PotionWorkbench.Owner")!=OWNER:raise RuntimeError("Preserve unowned asset "+path)
        return obj
    task=u.AssetImportTask();task.filename=str(source);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=False
    if options:task.options=options;task.factory=u.FbxFactory()
    else:task.factory=u.TextureFactory()
    A.import_asset_tasks([task])
    obj=u.load_asset(path)
    if not obj:raise RuntimeError("Import failed "+path)
    E.set_metadata_tag(obj,"PotionWorkbench.Owner",OWNER)
    return obj
def connect(a,socket,b,pin):
    if not L.connect_material_expressions(a,socket,b,pin):raise RuntimeError("Material pin failed "+pin)
def prop(a,socket,p):
    if not L.connect_material_property(a,socket,p):raise RuntimeError("Material output failed "+str(p))
def scalar(m,value):
    n=L.create_material_expression(m,u.MaterialExpressionConstant);n.r=float(value);return n
def color(m,value):
    n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*value,1);return n
receipt()
textures={}
for s in SPEC["materials"]:
    for role,source in s["textures"].items():
        if source in textures:continue
        name="T_PW_"+re.sub(r"[^A-Za-z0-9_]","_",Path(source).stem)
        tex=imp(source,name,DEST+"/Textures")
        tex.set_editor_property("srgb",role=="BaseColor")
        tex.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_NORMALMAP if role=="Normal"
            else u.TextureCompressionSettings.TC_MASKS if role in ("ORM","Roughness") else u.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property("max_texture_size",4096)
        if role=="Normal":tex.set_editor_property("flip_green_channel",True)
        save(tex);textures[source]=tex;report["textures"].append(tex.get_path_name());receipt()

mats={}
for s in SPEC["materials"]:
    name="M_"+s["slot"];path=DEST+"/Materials/"+name
    if E.does_asset_exist(path):
        mat=u.load_asset(path)
        if E.get_metadata_tag(mat,"PotionWorkbench.Owner")!=OWNER:raise RuntimeError("Preserve unowned material "+path)
        for n in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,n)
    else:mat=A.create_asset(name,DEST+"/Materials",u.Material,u.MaterialFactoryNew())
    mat.set_editor_property("used_with_instanced_static_meshes",True)
    transparent=s["transmission"]>0
    if transparent:
        mat.set_editor_property("blend_mode",u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property("shading_model",u.MaterialShadingModel.MSM_THIN_TRANSLUCENT)
        mat.set_editor_property("translucency_lighting_mode",u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        mat.set_editor_property("two_sided",False)
        thin=L.create_material_expression(mat,u.MaterialExpressionThinTranslucentMaterialOutput)
        # Authored glass uses actual wall thickness; use project-native thin translucent surfaces.
        tint=s["base_color"] if "glass" in s["slot"] else [min(.98,max(.015,v*(.5+.5*s["transmission"]))) for v in s["base_color"]]
        connect(color(mat,tint),"",thin,str(L.get_material_expression_input_names(thin)[0]))
        prop(scalar(mat,0),"",u.MaterialProperty.MP_OPACITY)
        slab=None
    else:
        slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
        slab.set_editor_property("shading_model_override",u.MaterialShadingModel.MSM_DEFAULT_LIT)
        prop(slab,"",u.MaterialProperty.MP_FRONT_MATERIAL)
    nodes={}
    for role,source in s["textures"].items():
        n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=textures[source]
        n.set_editor_property("sampler_type",u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=="Normal"
            else u.MaterialSamplerType.SAMPLERTYPE_MASKS if role in ("ORM","Roughness") else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        nodes[role]=n
    def output(node,socket,pin,kind):
        prop(node,socket,kind)
        if slab:connect(node,socket,slab,pin)
    base=nodes.get("BaseColor") or color(mat,s["base_color"])
    output(base,"RGB" if "BaseColor" in nodes else "","BaseColor",u.MaterialProperty.MP_BASE_COLOR)
    rough=nodes.get("ORM") or nodes.get("Roughness") or scalar(mat,s["roughness"])
    output(rough,"G" if "ORM" in nodes else "R" if "Roughness" in nodes else "","Roughness",u.MaterialProperty.MP_ROUGHNESS)
    metallic=nodes.get("ORM") or scalar(mat,s["metallic"])
    output(metallic,"B" if "ORM" in nodes else "","Metallic",u.MaterialProperty.MP_METALLIC)
    if "Normal" in nodes:output(nodes["Normal"],"RGB","Normal",u.MaterialProperty.MP_NORMAL)
    if "ORM" in nodes:prop(nodes["ORM"],"R",u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if s["emission_strength"]>0:
        em=color(mat,[v*s["emission_strength"] for v in s["emission_color"]])
        output(em,"","Emissive Color",u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError("Material compilation failed "+name+" "+str(errors))
    L.layout_material_expressions(mat);save(mat);mats[s["slot"]]=mat
    report["materials"].append(mat.get_path_name());receipt()

u.load_module("StaticMeshEditor")
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.one_convex_hull_per_ucx=True
d.generate_lightmap_u_vs=False;d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=False
d.transform_vertex_to_absolute=True;d.remove_degenerates=False
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
mesh=imp(SPEC["lods"][0]["source"],SPEC["mesh"],DEST+"/Meshes",opt)
for entry in SPEC["lods"][1:]:
    lod=entry["lod"]
    if SM.get_lod_count(mesh)<=lod:
        result=SM.import_lod(mesh,lod,entry["source"])
        if result!=lod:raise RuntimeError("LOD import did not complete "+str(result))
canon=lambda s:re.sub(r"[^a-z0-9]","",str(s).lower())
lookup={canon(k):v for k,v in mats.items()}
for i,slot in enumerate(mesh.static_materials):
    key=canon(slot.material_slot_name)
    if key not in lookup:raise RuntimeError("Unknown material slot "+str(slot.material_slot_name))
    mesh.set_material(i,lookup[key])
for lod in range(SM.get_lod_count(mesh)):
    settings=SM.get_lod_build_settings(mesh,lod)
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
    settings.generate_lightmap_u_vs=False;settings.remove_degenerates=False
    SM.set_lod_build_settings(mesh,lod,settings)
SM.set_lod_screen_sizes(mesh,[1.0,.45,.18])
# This buildable contains actual transparent glass and liquids in one mesh.
nan=mesh.get_editor_property("nanite_settings");nan.enabled=False;SM.set_nanite_settings(mesh,nan,True)
body=mesh.get_editor_property("body_setup");body.set_editor_property("collision_trace_flag",u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
save(mesh)
bounds=mesh.get_bounds()
report["mesh"]={"path":mesh.get_path_name(),"bounds_origin_cm":[bounds.origin.x,bounds.origin.y,bounds.origin.z],
    "bounds_extent_cm":[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z],
    "lods":SM.get_lod_count(mesh),"authored_triangles":[s["triangles"] for s in SPEC["lods"]],
    "convex_collision_count":SM.get_convex_collision_count(mesh),
    "materials":[{"slot":str(s.material_slot_name),"material":s.material_interface.get_path_name()} for s in mesh.static_materials],
    "collision":"simple_and_complex","nanite":False}
report["stage"]="staged_assets_saved";receipt();u.log("POTION_WORKBENCH_ASSETS_SAVED")
