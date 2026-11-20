"""Save two quarry finish materials and the scar and blank that use them."""
import json
from pathlib import Path
import sys
import unreal as ue

tool_dir = str(Path(__file__).resolve().parent)
if tool_dir not in sys.path:
    sys.path.insert(0, tool_dir)
from quarry_spoil_surface import apply_weathered_finish

project=Path(__file__).resolve().parents[3]
src=project/"SourceAssets/HillsQuarryCutYard"
dest="/Game/WorldGeneration/TemperateHills/WhiteCliffs"
tools=ue.AssetToolsHelpers.get_asset_tools()
lib=ue.MaterialEditingLibrary
materials={}

def connect(a,output,b,pin):
    if not lib.connect_material_expressions(a,output,b,pin):
        raise RuntimeError("Unconnected material input "+pin)

for slot,texture in (("WeatheredBed","CliffSurface_03A"),("FreshBreak","StoneSurface_03A")):
    name="M_Quarry"+slot
    folder=dest+"/Materials/CutYard"
    path=folder+"/"+name
    mat=ue.load_asset(path) if ue.EditorAssetLibrary.does_asset_exist(path) else tools.create_asset(name,folder,ue.Material,ue.MaterialFactoryNew())
    for expression in list(lib.get_material_expressions(mat)):
        lib.delete_material_expression(mat, expression)
    mat.set_editor_property("used_with_instanced_static_meshes",True)
    mat.set_editor_property("used_with_nanite",True)
    def node(cls):
        return lib.create_material_expression(mat,cls)
    uv=node(ue.MaterialExpressionTextureCoordinate)
    is_fresh=slot=="FreshBreak"
    for suffix,typ in (("BaseColor",ue.MaterialSamplerType.SAMPLERTYPE_COLOR),("Normal",ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)):
        sample=node(ue.MaterialExpressionTextureSample)
        sample.texture=ue.load_asset("/Game/UnrealNormandy/Textures/T_"+texture+"_"+suffix)
        if not sample.texture: raise RuntimeError("Missing surface texture "+texture+"_"+suffix)
        sample.sampler_type=typ
        connect(uv,"",sample,"UVs")
        if suffix=="BaseColor":
            color=node(ue.MaterialExpressionCustom)
            inputs=[]
            for key in ("Rock","Metres"):
                value=ue.CustomInput()
                value.set_editor_property("input_name",key)
                inputs.append(value)
            color.set_editor_property("inputs",inputs)
            color.set_editor_property("output_type",ue.CustomMaterialOutputType.CMOT_FLOAT3)
            # UVs are metres. The broad, wandering bands cross the stone texture tiles.
            color.set_editor_property("code","""
float l = dot(Rock,float3(.2126,.7152,.0722));
float band = .5+.5*sin(Metres.y*2.6 + .42*sin(Metres.x*.58) + .16*Metres.x);
float stain = smoothstep(.25,.80,.5+.27*sin(Metres.x*.52+Metres.y*.33)+.22*sin(Metres.y*.84-Metres.x*.39));
""" + ("""
return (.16+.51*sqrt(saturate(l)))*float3(1.04,.92,.76)*(.95+.05*band);
""" if is_fresh else """
return lerp(Rock*.39+float3(.095,.091,.077),float3(.19,.179,.146)+l*.27,.44)
       *(.84+.16*band)*(1.-.22*stain);
"""))
            connect(sample,"RGB",color,"Rock")
            connect(uv,"",color,"Metres")
            if not lib.connect_material_property(color,"",ue.MaterialProperty.MP_BASE_COLOR):raise RuntimeError("BaseColor")
        elif not lib.connect_material_property(sample,"RGB",ue.MaterialProperty.MP_NORMAL):raise RuntimeError("Normal")
    rough=node(ue.MaterialExpressionConstant)
    rough.r=.81 if is_fresh else .89
    lib.connect_material_property(rough,"",ue.MaterialProperty.MP_ROUGHNESS)
    apply_weathered_finish(mat)
    errors = lib.recompile_material(mat)
    if errors or not ue.EditorAssetLibrary.save_loaded_asset(mat, False):
        raise RuntimeError(f"{path}: {errors}")
    materials[slot]=mat

saved=[]
for spec in json.loads((src/"mesh-manifest.json").read_text(encoding="utf8")):
    name=spec["name"]
    folder=dest+"/Meshes/Fractures"
    task=ue.AssetImportTask()
    task.filename=str(src/(name+".fbx"))
    task.destination_path=folder
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    task.replace_existing_settings=True
    options=ue.FbxImportUI()
    options.import_materials=False
    options.import_textures=False
    options.mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH
    static=options.static_mesh_import_data
    static.combine_meshes=True
    static.auto_generate_collision=False
    static.generate_lightmap_u_vs=False
    static.normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=options
    tools.import_asset_tasks([task])
    mesh=ue.load_asset(folder+"/"+name)
    if not mesh or not task.imported_object_paths:raise RuntimeError(name)
    for i,binding in enumerate(mesh.static_materials):
        mesh.set_material(i,materials[str(binding.material_slot_name)])
    settings=mesh.get_editor_property("nanite_settings")
    settings.enabled=True
    settings.fallback_percent_triangles=1.
    settings.fallback_relative_error=0.
    mesh.set_editor_property("nanite_settings",settings)
    mesh.get_editor_property("body_setup").set_editor_property("collision_trace_flag",ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not ue.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError(name)
    if name=="SM_QuarryBenchScar":
        # The dressed face must point into the yard after FBX axis conversion.
        dm,status=ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,ue.DynamicMesh(),
            ue.GeometryScriptCopyMeshFromAssetOptions(),ue.GeometryScriptMeshReadLOD())
        if status!=ue.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Cannot read the imported scar")
        query=ue.GeometryScript_MeshQueries
        _,verts,_=query.get_all_vertex_positions(dm,False)
        _,indices,_=query.get_all_triangle_indices(dm,False)
        pts=ue.GeometryScript_List.convert_vector_list_to_array(verts)
        triangles=ue.GeometryScript_List.convert_triangle_list_to_array(indices)
        fresh_slot=next(i for i,s in enumerate(mesh.static_materials) if str(s.material_slot_name)=="FreshBreak")
        normal=ue.Vector(0,0,0)
        for i,t in enumerate(triangles):
            if ue.GeometryScript_Materials.get_triangle_material_id(dm,i)[0]!=fresh_slot:continue
            a,b,c=(pts[j] for j in (t.x,t.y,t.z))
            normal+=(c-a).cross(b-a)
        if normal.y>=-abs(normal.x):raise RuntimeError("Fresh break faces away from the haul yard")
        box=mesh.get_bounding_box()
        def xyz(v):return [round(v.x,3),round(v.y,3),round(v.z,3)]
        orientation={"ue_size_cm":xyz(box.max-box.min),"fresh_outward_area":xyz(normal),"triangles":len(triangles)}
        (src/"import-orientation.json").write_text(json.dumps(orientation,indent=2),encoding="utf8")
    saved.append({"mesh":mesh.get_path_name(),"materials":[s.material_interface.get_path_name() for s in mesh.static_materials]})
(src/"saved.json").write_text(json.dumps(saved,indent=2),encoding="utf8")

# The scanned faces, cuts and loose stone use the same rain response as the blanks.
for name in ("CliffA", "CliffB", "LimestoneCut", "LimestoneSpoil"):
    path = dest + "/Materials/M_" + name
    mat = ue.load_asset(path)
    if not mat:
        raise RuntimeError("Missing placed stone material " + path)
    if apply_weathered_finish(mat):
        errors = lib.recompile_material(mat)
        if errors or not ue.EditorAssetLibrary.save_loaded_asset(mat, False):
            raise RuntimeError(f"{path}: {errors}")
