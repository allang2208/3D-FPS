"""Import the permanent meshes and ground finish for the White Cliffs entrance."""
from pathlib import Path
import os
import sys
import unreal as ue

tool_dir = str(Path(__file__).resolve().parent)
if tool_dir not in sys.path:
    sys.path.insert(0, tool_dir)
from quarry_stone_relief import apply_stone_relief

source = Path(__file__).resolve().parents[3] / "SourceAssets/HillsQuarryCutYard/Approach"
quarry = "/Game/WorldGeneration/TemperateHills/WhiteCliffs"
surfaces = quarry + "/Materials/Approach"
meshes = quarry + "/Meshes/Approach"
assets = ue.EditorAssetLibrary
library = ue.MaterialEditingLibrary
tools = ue.AssetToolsHelpers.get_asset_tools()
output = ue.CustomMaterialOutputType
props = ue.MaterialProperty


def require(path):
    asset = ue.load_asset(path)
    if not asset:
        raise RuntimeError("Missing quarry dependency " + path)
    return asset


def save(asset):
    if not assets.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + asset.get_path_name())


def material(name):
    path = surfaces + "/" + name
    mat = require(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, surfaces, ue.Material, ue.MaterialFactoryNew())
    for expression in list(library.get_material_expressions(mat)):
        library.delete_material_expression(mat, expression)
    return mat


def node(mat, kind):
    return library.create_material_expression(mat, kind)


def wire(source_pin, target, pin):
    expr, channel = source_pin if isinstance(source_pin, tuple) else (source_pin, "")
    if not library.connect_material_expressions(expr, channel, target, pin):
        raise RuntimeError("Could not connect " + expr.get_name() + " to " + pin)


def custom(mat, kind, label, inputs, code):
    expr = node(mat, ue.MaterialExpressionCustom)
    expr.set_editor_property("desc", label)
    pins = []
    for name in inputs:
        pin = ue.CustomInput()
        pin.set_editor_property("input_name", name)
        pins.append(pin)
    expr.set_editor_property("inputs", pins)
    expr.set_editor_property("output_type", kind)
    expr.set_editor_property("code", code)
    for name, upstream in inputs.items():
        wire(upstream, expr, name)
    return expr


def bind(mat_prop, expr, channel=""):
    if not library.connect_material_property(expr, channel, mat_prop):
        raise RuntimeError("Cannot bind " + str(mat_prop))


def texture(mat, asset, uv, sampler):
    tex = node(mat, ue.MaterialExpressionTextureSample)
    tex.set_editor_property("texture", asset)
    tex.set_editor_property("sampler_type", sampler)
    wire(uv, tex, "UVs")
    return tex


def wetness(mat):
    expr = node(mat, ue.MaterialExpressionCollectionParameter)
    expr.set_editor_property("collection", require("/Game/Weather/Materials/MPC_FPS_Weather"))
    expr.set_editor_property("parameter_name", "WeatherWetness")
    return expr


def finish(mat):
    diagnostics = library.recompile_material(mat)
    if diagnostics:
        raise RuntimeError(mat.get_name() + " " + str(diagnostics))
    save(mat)
    return mat


def limestone(name):
    fresh=name=="TooledLime"
    scan="StoneSurface_03A" if fresh else "CliffSurface_03A"
    mat = material("M_Quarry" + name)
    mat.set_editor_property("used_with_nanite", True)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    uv = node(mat, ue.MaterialExpressionTextureCoordinate)
    field = node(mat, ue.MaterialExpressionVertexColor)
    wet = wetness(mat)
    prefix = "/Game/UnrealNormandy/Textures/T_" + scan
    albedo = texture(mat, require(prefix + "_BaseColor"), uv, ue.MaterialSamplerType.SAMPLERTYPE_COLOR)
    normal = texture(mat, require(prefix + "_Normal"), uv, ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    macro_uv=custom(mat,output.CMOT_FLOAT2,"Mineral patches across fracture planes",{"UV":uv},
                    "return float2(.241*UV.x-.137*UV.y,.137*UV.x+.241*UV.y)+float2(.28,.73);")
    macro=texture(mat,require(prefix+"_BaseColor"),macro_uv,ue.MaterialSamplerType.SAMPLERTYPE_COLOR)
    base = """
float lum = dot(Rock, float3(.2126,.7152,.0722));
float3 stone = lerp(Rock, lum.xxx, .57);
""" + ("""
stone = float3(.145,.111,.067) + .46 * stone;
float u=Metres.x/.46;
float tooth=u/.255+.095*sin(Metres.y*3.1)+.105*sin(u*1.18);
float slot=1.-smoothstep(.035,.21,abs(frac(tooth+.5)-.5));
float fade=1.-smoothstep(.18,.69,fwidth(tooth));
stone*=1.-.24*slot*fade*Weathering.g;
""" if fresh else """
stone = float3(.095,.085,.065) + .54 * stone;
""" if name=="RivenLime" else """
stone = float3(.040,.039,.033) + .57 * stone;
""") + """
float mineral=smoothstep(.11,.61,dot(Mineral,float3(.213,.715,.072)));
stone *= lerp(float3(.78,.77,.73),float3(1.13,1.08,1.),mineral);
stone *= lerp(float3(1,1,1),float3(.76,.66,.53),Weathering.b*.82);
""" + ("" if fresh else """
stone *= lerp(float3(1,1,1),float3(.59,.70,.47),Weathering.g*.82);
""") + """
stone = lerp(stone,stone*float3(.71,.66,.55),Weathering.r*.75);
return stone * (1.-saturate(Wet)*(.18+.13*Weathering.r+.06*Weathering.b));
"""
    bind(props.MP_BASE_COLOR, custom(mat, output.CMOT_FLOAT3, "Limestone and seepage",
                                    {"Rock": (albedo, "RGB"), "Weathering": field, "Wet": wet,
                                     "Mineral":(macro,"RGB"),"Metres":uv}, base))
    bind(props.MP_NORMAL, normal, "RGB")
    rough = "return lerp(.80+.08*Base,.52+.10*Base,saturate(Wet));" if fresh else (
        "return lerp(.83+.10*Base,.48+.16*Base,saturate(Wet));")
    bind(props.MP_ROUGHNESS, custom(mat, output.CMOT_FLOAT1, "Wet surface roughness",
                                   {"Base": (albedo, "R"), "Wet": wet}, rough))
    apply_stone_relief(mat)
    return finish(mat)


def hemp():
    mat = material("M_QuarryHemp")
    mat.set_editor_property("used_with_nanite", True)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    uv = node(mat, ue.MaterialExpressionTextureCoordinate)
    bind(props.MP_BASE_COLOR, custom(mat, output.CMOT_FLOAT3, "Twisted hemp fibres",
        {"Metres": uv, "Wet": wetness(mat)}, """
float twist=dot(Metres,float2(680.,490.));
float fade=1.-smoothstep(.65,3.,fwidth(twist));
float fibre=.56+.25*sin(twist)*fade+.12*sin(2.*twist)*fade;
return lerp(float3(.13,.092,.051),float3(.25,.199,.119),fibre)*(1.-.26*saturate(Wet));
"""))
    rough = node(mat, ue.MaterialExpressionConstant)
    rough.r = .91
    bind(props.MP_ROUGHNESS, rough)
    return finish(mat)


def import_file(name, extension, folder, options=None):
    task = ue.AssetImportTask()
    task.filename = str(source / (name + extension))
    task.destination_name = name
    task.destination_path = folder
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    if options:
        task.options = options
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError("Could not import " + task.filename)
    return require(folder + "/" + name)


def ground_mask(name,compression):
    mask = import_file(name, ".png", surfaces)
    mask.set_editor_property("compression_settings", compression)
    mask.set_editor_property("srgb", False)
    mask.set_editor_property("address_x", ue.TextureAddress.TA_CLAMP)
    mask.set_editor_property("address_y", ue.TextureAddress.TA_CLAMP)
    mask.set_editor_property("virtual_texture_streaming", False)
    save(mask)
    return mask


def ground():
    mask = ground_mask("T_QuarryWorkGround",ue.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
    spalls = ground_mask("T_QuarryDressingSpalls",ue.TextureCompressionSettings.TC_MASKS)
    mat = material("M_QuarryWorkGround")
    mat.set_editor_property("material_domain", ue.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property("blend_mode", ue.BlendMode.BLEND_TRANSLUCENT)
    pos = node(mat, ue.MaterialExpressionWorldPosition)
    survey = node(mat, ue.MaterialExpressionVectorParameter)
    survey.set_editor_property("parameter_name", "Survey")
    survey.set_editor_property("default_value", ue.LinearColor(0, 0, 1, 0))
    datum = node(mat, ue.MaterialExpressionScalarParameter)
    datum.set_editor_property("parameter_name", "FloorZ")
    uv = custom(mat, output.CMOT_FLOAT2, "Survey coordinates",
                {"P": pos, "Frame": (survey, "RGB"), "AxisY": (survey, "A")}, """
float2 d=P.xy-Frame.xy;
float2 local=float2(dot(d,float2(Frame.z,AxisY)),dot(d,float2(-AxisY,Frame.z)));
return (local+float2(3500.,4000.))/float2(7000.,9200.);
""")
    atlas = texture(mat, mask, uv, ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    fines = texture(mat,spalls,uv,ue.MaterialSamplerType.SAMPLERTYPE_MASKS)
    fine_uv = custom(mat, output.CMOT_FLOAT2, "Earth metres", {"P": pos}, "return P.xy/155.;")
    grit_uv = custom(mat, output.CMOT_FLOAT2, "Gravel metres", {"P": pos},
                     "return float2(.91*P.x+.42*P.y,-.42*P.x+.91*P.y)/169.;")
    earth = texture(mat, require("/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_B"),
                    fine_uv, ue.MaterialSamplerType.SAMPLERTYPE_COLOR)
    grit = texture(mat, require("/Game/UnrealNormandy/Textures/T_LC_GroundRockyRoad_00A_Albedo"), grit_uv,
                   ue.MaterialSamplerType.SAMPLERTYPE_COLOR)
    earth_prefix="/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_"
    grit_prefix="/Game/UnrealNormandy/Textures/T_LC_GroundRockyRoad_00A_"
    earth_n=texture(mat,require(earth_prefix+"N"),fine_uv,ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    grit_n=texture(mat,require(grit_prefix+"Normal"),grit_uv,ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    wet = wetness(mat)
    stones=custom(mat,output.CMOT_FLOAT1,"Gravel breaks through the soil",
        {"Bank":(atlas,"G"),"Stone":(grit,"R"),"Soil":(earth,"R")},
        "return smoothstep(.16,.85,Bank+(Stone-.24)*.78-(Soil-.19)*.37);")
    bind(props.MP_BASE_COLOR, custom(mat, output.CMOT_FLOAT3, "Cart lane and talus",
        {"Earth": (earth,"RGB"), "Gravel": (grit,"RGB"), "Coarse": stones, "Damp": (atlas,"A"), "Wet": wet,
         "Spall":(fines,"B"),"Powder":(fines,"A")}, """
float3 tamped=lerp(Earth,dot(Earth,float3(.213,.715,.072)).xxx,.36)*float3(.67,.63,.54)+float3(.018,.017,.014);
float3 chips=lerp(Gravel,dot(Gravel,float3(.213,.715,.072)).xxx,.46)*float3(.86,.84,.76)+float3(.037,.035,.030);
float wet=saturate(Wet);
float grain=dot(Gravel,float3(.213,.715,.072));
float3 ground=lerp(tamped,chips,Coarse);
float3 dust=float3(.080,.075,.062)+(.44*grain+.22*dot(Earth,float3(.213,.715,.072)))*float3(1.,.96,.83);
ground=lerp(ground,dust,Powder*.84)*(1.-.15*Damp)*(1.-(.18+.33*Damp+.06*Powder)*wet);
float3 lime=(float3(.11,.10,.084)+.70*grain*float3(1.,.96,.87))*(1.-.24*wet);
return lerp(ground,lime,Spall*.92);
"""))
    mat.set_editor_property("tangent_space_normal",False)
    bind(props.MP_NORMAL,custom(mat,output.CMOT_FLOAT3,"Metric stone and soil relief",
        {"EarthN":(earth_n,"RGB"),"StoneN":(grit_n,"RGB"),"Coarse":stones,"P":pos,
         "Fines":(fines,"RGB"),"Powder":(fines,"A"),"AxisX":(survey,"B"),"AxisY":(survey,"A")}, """
float3 base=normalize(cross(ddy(P),ddx(P))+float3(0.,0.,.000001));
base*=base.z<0.?-1.:1.;
float2 detail=lerp(EarthN.xy,float2(.91*StoneN.x-.42*StoneN.y,.42*StoneN.x+.91*StoneN.y),Coarse);
float2 slope=(Fines.rg*2.-1.)*saturate(Fines.b*5.);
float2 fracture=float2(AxisX*slope.x-AxisY*slope.y,AxisY*slope.x+AxisX*slope.y);
return normalize(base+float3(detail*lerp(.54,.83,Coarse)*(1.-.34*Powder)+fracture,0.));
"""))
    bind(props.MP_ROUGHNESS, custom(mat, output.CMOT_FLOAT1, "Damp wheel ruts",
        {"Coarse":stones,"Damp":(atlas,"A"),"Micro":(grit,"R"),"Wet":wet},
        "return lerp(.77+.11*Coarse+.08*Micro,.65-.31*Damp+.09*Micro,saturate(Wet));"))
    bind(props.MP_OPACITY, custom(mat, output.CMOT_FLOAT1, "Ground height and frayed edges",
        {"SurveyMap": (atlas,"RGB"), "P": pos, "Datum": datum, "TextureGrain": (grit,"R")}, """
float distanceZ=abs(P.z-Datum-(SurveyMap.b*2400.-200.));
float coverage=saturate(SurveyMap.r+(TextureGrain-.35)*.28*(1.-SurveyMap.r))*smoothstep(.015,.18,SurveyMap.r);
float3 face=cross(ddy(P),ddx(P));
float up=abs(face.z)*rsqrt(max(dot(face,face),1e-12));
return coverage*(1.-smoothstep(12.,38.,distanceZ))*smoothstep(.63,.91,up);
"""))
    finish(mat)


def load_mesh(name, materials, cliff):
    options = ue.FbxImportUI()
    options.import_materials = False
    options.import_textures = False
    options.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = False
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option = ue.VertexColorImportOption.REPLACE
    mesh = import_file(name, ".fbx", meshes, options)
    for index, slot in enumerate(mesh.static_materials):
        mesh.set_material(index, materials[str(slot.material_slot_name)])
    nanite = mesh.get_editor_property("nanite_settings")
    nanite.enabled = True
    nanite.fallback_percent_triangles = .38 if cliff else 1.
    nanite.fallback_relative_error = .15 if cliff else 0.
    mesh.set_editor_property("nanite_settings", nanite)
    mesh.get_editor_property("body_setup").set_editor_property("collision_trace_flag",
        ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh)


def work_materials(rope):
    return dict(Blank=require(quarry + "/Materials/CutYard/M_QuarryFreshBreak"),
                Oak=require(quarry + "/Materials/Quarry_M_OakDry"),
                Iron=require(quarry + "/Materials/Quarry_MI_DarkForgedIron"),Rope=rope)

walls_only=os.environ.get("QUARRY_WALLS_ONLY")=="1"
derrick_only=os.environ.get("QUARRY_DERRICK_ONLY")=="1"
if not walls_only and not derrick_only:ground()
if derrick_only:
    bindings=work_materials(require(surfaces+"/M_QuarryHemp"))
    bindings["Bedded"]=require(surfaces+"/M_QuarryBeddedLime")
    load_mesh("SM_QuarryYardDerrick",bindings,False)
elif os.environ.get("QUARRY_GROUND_ONLY")!="1":
    bindings = {slot:limestone(name) for slot,name in
                (("Bedded","BeddedLime"),("Tooled","TooledLime"),("Riven","RivenLime"))}
    for model in ("WestWorkingFace","EastLifts","SlipPlate","KeyBlock"):
        load_mesh("SM_Quarry"+model,bindings,model in ("WestWorkingFace","EastLifts"))
    if not walls_only:
        bindings.update(work_materials(hemp()))
        for model in ("YardDerrick","DressingBench"):load_mesh("SM_Quarry"+model,bindings,False)
ue.log("QUARRY_APPROACH_PACKAGES_SAVED")
