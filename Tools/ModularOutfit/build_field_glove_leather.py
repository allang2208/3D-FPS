"""Rebuild the two field-glove materials from licensed leather scans and V7 masks."""
import json
import time
from pathlib import Path

import unreal as u

PROJECT = Path("D:/FPS3D/FPSGAME")
AUTHOR = PROJECT/"SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1"
SOURCE = PROJECT/"SourceAssets/HandEquipmentAppearance/Source"
DEST = "/Game/Characters/ModularOutfit20260924/Materials"
TEX = DEST+"/Textures"
LEATHER = "/Game/Characters/ArmsLeatherCandidate/Textures"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
code = (AUTHOR/"field_glove_leather.hlsl").read_text(encoding="utf-8")

def play_world():
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world:
        return None
    name = world.get_name()
    print("FIELD_GLOVES_WORLD", name, flush=True)
    if "UEDPIE" in name or name.startswith("UEDPIE") or "PIE_" in name:
        return world
    return None

world = play_world()
if world:
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    for _ in range(80):
        time.sleep(0.25)
        if not play_world():
            break
    else:
        raise RuntimeError("Could not end play before saving field glove leather")


def save(asset):
    pkg = asset.get_outer()
    if u.EditorLoadingAndSavingUtils.save_packages([pkg], False):
        return
    if E.save_loaded_asset(asset, False):
        return
    path = Path(str(u.SystemLibrary.get_project_content_directory())) / (
        asset.get_path_name().split(".", 1)[0].replace("/Game/", "") + ".uasset")
    if path.exists():
        print("FIELD_GLOVES_SAVE_EXISTING", asset.get_path_name(), flush=True)
        return
    raise RuntimeError("Did not save "+asset.get_path_name())


def import_texture(filename, name, kind, flip_green=False, dest=TEX):
    path = dest+"/"+name
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    A.import_asset_tasks([task])
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError("Missing imported texture "+path)
    asset.set_editor_property("srgb", kind == "color")
    asset.set_editor_property("compression_settings", {
        "color": u.TextureCompressionSettings.TC_DEFAULT,
        "normal": u.TextureCompressionSettings.TC_NORMALMAP,
        "mask": u.TextureCompressionSettings.TC_MASKS,
        "gray": u.TextureCompressionSettings.TC_GRAYSCALE,
    }[kind])
    if kind == "normal":
        asset.set_editor_property("flip_green_channel", flip_green)
    save(asset)
    return asset


def clear(mat):
    mat.modify()
    for expr in list(L.get_material_expressions(mat)):
        L.delete_material_expression(mat, expr)
    leftover = list(L.get_material_expressions(mat))
    if leftover:
        raise RuntimeError("Could not clear "+mat.get_path_name())


def node(mat, cls, **props):
    n = L.create_material_expression(mat, cls)
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n


def wire(a, b, pin, output=""):
    if not L.connect_material_expressions(a, output, b, pin):
        raise RuntimeError("Cannot connect "+pin)


def sample(mat, name, path, kind, uv=None):
    tex = u.load_asset(path)
    if not tex:
        raise RuntimeError("Missing leather texture "+path)
    n = node(mat, u.MaterialExpressionTextureSampleParameter2D,
             parameter_name=name, texture=tex, sampler_type=kind)
    if uv:
        wire(uv, n, "UVs")
    return n


def texture_object(mat, name, path, kind):
    tex = u.load_asset(path)
    if not tex:
        raise RuntimeError("Missing leather texture "+path)
    return node(mat, u.MaterialExpressionTextureObjectParameter,
                parameter_name=name, texture=tex, sampler_type=kind)


def interpolate(mat, expression):
    out = node(mat, u.MaterialExpressionVertexInterpolator)
    wire(expression, out, "")
    return out


def world_axis(mat, axis):
    out = node(mat, u.MaterialExpressionTransform,
               transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
               transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(node(mat, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(*axis, 1)), out, "")
    return out


for required in (
    AUTHOR/"T_FieldGloves_LeatherRegions.png",
    AUTHOR/"T_FieldGloves_StitchNormal.png",
    AUTHOR/"T_FieldGloves_CuffField.png",
    AUTHOR/"T_FieldGloves_CuffRollNormal.png",
    AUTHOR/"T_FieldGloves_Wear.png",
):
    if not required.is_file():
        raise RuntimeError("Missing field glove leather source "+str(required))
ao_src = SOURCE/"Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_AO.jpg"
cavity_src = SOURCE/"Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Cavity.jpg"
spec_src = SOURCE/"Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Specular.jpg"
if not ao_src.is_file() or not cavity_src.is_file() or not spec_src.is_file():
    raise RuntimeError("Missing Quixel AO/Cavity/Specular scans")
if not u.load_asset(LEATHER+"/T_Fab_Leather_BaseColor"):
    raise RuntimeError("Missing shared leather scan "+LEATHER+"/T_Fab_Leather_BaseColor")
if not u.load_asset(LEATHER+"/T_Fab_Leather_Normal"):
    raise RuntimeError("Missing shared leather scan "+LEATHER+"/T_Fab_Leather_Normal")

E.make_directory(TEX)
import_texture(AUTHOR/"T_FieldGloves_LeatherRegions.png", "T_FieldGloves_LeatherRegions", "mask")
import_texture(AUTHOR/"T_FieldGloves_StitchNormal.png", "T_FieldGloves_StitchNormal", "normal", False)
import_texture(AUTHOR/"T_FieldGloves_CuffField.png", "T_FieldGloves_CuffField", "gray")
import_texture(AUTHOR/"T_FieldGloves_CuffRollNormal.png", "T_FieldGloves_CuffRollNormal", "normal", False)
import_texture(AUTHOR/"T_FieldGloves_Wear.png", "T_FieldGloves_Wear", "gray")
import_texture(ao_src, "T_Fab_Leather_AO", "gray", dest=LEATHER)
import_texture(cavity_src, "T_Fab_Leather_Cavity", "gray", dest=LEATHER)
import_texture(spec_src, "T_Fab_Leather_Specular", "gray", dest=LEATHER)


def build_leather(mat, tint_amount, color_tint, extras=None):
    extras = extras or {}
    clear(mat)
    mat.set_editor_property("shading_model", u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("used_with_skeletal_mesh", True)
    L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_STATIC_MESH)
    uv = node(mat, u.MaterialExpressionTextureCoordinate)
    color_type = u.MaterialSamplerType.SAMPLERTYPE_COLOR
    normal_type = u.MaterialSamplerType.SAMPLERTYPE_NORMAL
    mask_type = u.MaterialSamplerType.SAMPLERTYPE_MASKS
    gray_type = u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
    linear_type = u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    inputs = {
        "UV": uv,
        "RestPosition": interpolate(mat, node(mat, u.MaterialExpressionPreSkinnedPosition)),
        "RestNormal": interpolate(mat, node(mat, u.MaterialExpressionPreSkinnedNormal)),
        "Regions": sample(mat, "LeatherRegions", TEX+"/T_FieldGloves_LeatherRegions", mask_type),
        "WearMask": sample(mat, "WearMask", TEX+"/T_FieldGloves_Wear", gray_type),
        "Thread": sample(mat, "StitchNormal", TEX+"/T_FieldGloves_StitchNormal", normal_type),
        "CuffField": sample(mat, "CuffField", TEX+"/T_FieldGloves_CuffField", gray_type),
        "RollNormal": sample(mat, "CuffRollNormal", TEX+"/T_FieldGloves_CuffRollNormal", normal_type),
        "LeatherColor": texture_object(mat, "LeatherColor", LEATHER+"/T_Fab_Leather_BaseColor", color_type),
        "LeatherRoughTex": texture_object(mat, "LeatherRoughTex", LEATHER+"/T_Fab_Leather_Roughness", linear_type),
        "LeatherNormal": texture_object(mat, "LeatherNormal", LEATHER+"/T_Fab_Leather_Normal", linear_type),
        "LeatherAO": texture_object(mat, "LeatherAO", LEATHER+"/T_Fab_Leather_AO", gray_type),
        "LeatherCavity": texture_object(mat, "LeatherCavity", LEATHER+"/T_Fab_Leather_Cavity", gray_type),
        "LeatherSpec": texture_object(mat, "LeatherSpec", LEATHER+"/T_Fab_Leather_Specular", gray_type),
        "ColorTint": node(mat, u.MaterialExpressionVectorParameter, parameter_name="ColorTint",
                          default_value=u.LinearColor(*color_tint, 1)),
        "TintAmount": node(mat, u.MaterialExpressionScalarParameter, parameter_name="TintAmount", default_value=tint_amount),
        "ColorMidpoint": node(mat, u.MaterialExpressionScalarParameter, parameter_name="ColorMidpoint", default_value=extras.get("ColorMidpoint", 0.06943667240440846)),
        "LeatherTileCm": node(mat, u.MaterialExpressionScalarParameter, parameter_name="LeatherTileCm", default_value=25),
        "LeatherNormalStrength": node(mat, u.MaterialExpressionScalarParameter, parameter_name="LeatherNormalStrength", default_value=extras.get("LeatherNormalStrength", 0.36)),
        "LeatherNormalMip": node(mat, u.MaterialExpressionScalarParameter, parameter_name="LeatherNormalMip", default_value=extras.get("LeatherNormalMip", 1.1)),
        "LeatherAOAmount": node(mat, u.MaterialExpressionScalarParameter, parameter_name="LeatherAOAmount", default_value=extras.get("LeatherAOAmount", 0.30)),
        "LeatherCavityAmount": node(mat, u.MaterialExpressionScalarParameter, parameter_name="LeatherCavityAmount", default_value=extras.get("LeatherCavityAmount", 0.18)),
        "PalmGrainScale": node(mat, u.MaterialExpressionScalarParameter, parameter_name="PalmGrainScale", default_value=extras.get("PalmGrainScale", 0.32)),
        "GloveSpecular": node(mat, u.MaterialExpressionScalarParameter, parameter_name="GloveSpecular", default_value=0.35),
        "SpecMidpoint": node(mat, u.MaterialExpressionScalarParameter, parameter_name="SpecMidpoint", default_value=0.196),
        "LeatherMacroTileCm": node(mat, u.MaterialExpressionScalarParameter, parameter_name="LeatherMacroTileCm", default_value=60),
        "ColorMacroAmount": node(mat, u.MaterialExpressionScalarParameter, parameter_name="ColorMacroAmount", default_value=extras.get("ColorMacroAmount", 0.22)),
        "WearAmount": node(mat, u.MaterialExpressionScalarParameter, parameter_name="WearAmount", default_value=extras.get("WearAmount", 1.0)),
        "CuffSpanM": node(mat, u.MaterialExpressionScalarParameter, parameter_name="CuffSpanM", default_value=0.012),
    }
    custom = node(mat, u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
                  description="V7 field glove leather; rest-pose triplanar AO/cavity/spec, worn palm, rolled cuff")
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property("input_name", name)
        pins.append(pin)
    custom.set_editor_property("inputs", pins)
    extras = []
    for name, kind in (("OutNormal", 3), ("OutRoughness", 1), ("OutSpecular", 1)):
        item = u.CustomOutput()
        item.set_editor_property("output_name", name)
        item.set_editor_property("output_type", getattr(u.CustomMaterialOutputType, "CMOT_FLOAT"+str(kind)))
        extras.append(item)
    custom.set_editor_property("additional_outputs", extras)
    for name, expr in inputs.items():
        wire(expr, custom, name)
    if not L.connect_material_property(custom, "", u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError("Cannot bind field glove base color")
    if not L.connect_material_property(custom, "OutNormal", u.MaterialProperty.MP_NORMAL):
        raise RuntimeError("Cannot bind field glove normal")
    if not L.connect_material_property(custom, "OutRoughness", u.MaterialProperty.MP_ROUGHNESS):
        raise RuntimeError("Cannot bind field glove roughness")
    if not L.connect_material_property(custom, "OutSpecular", u.MaterialProperty.MP_SPECULAR):
        raise RuntimeError("Cannot bind field glove specular")
    if not L.connect_material_property(node(mat, u.MaterialExpressionConstant, r=0), "", u.MaterialProperty.MP_METALLIC):
        raise RuntimeError("Cannot bind field glove metallic")
    L.layout_material_expressions(mat)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError("Field glove compilation failed: "+str(errors))
    save(mat)
    return mat


variants = {
    "M_FieldGloves_Leather": {"TintAmount": 0.0, "ColorTint": (1, 1, 1), "extras": {}},
    "M_FieldGloves_Brown": {"TintAmount": 0.0, "ColorTint": (1, 1, 1), "extras": {}},
    "M_FieldGloves_Black": {
        "TintAmount": 1.0, "ColorTint": (0.016, 0.018, 0.022),
        "extras": {
            "LeatherNormalStrength": 0.30, "LeatherNormalMip": 1.1, "LeatherAOAmount": 0.16,
            "LeatherCavityAmount": 0.10, "ColorMidpoint": 0.10, "PalmGrainScale": 0.28,
            "ColorMacroAmount": 0.22, "WearAmount": 1.0,
        },
    },
}
published = {}
for name, params in variants.items():
    path = DEST+"/"+name
    mat = u.load_asset(path)
    if mat and not isinstance(mat, u.Material):
        raise RuntimeError("Unexpected asset type for "+path)
    if not mat:
        mat = A.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    build_leather(mat, params["TintAmount"], params["ColorTint"], params.get("extras"))
    amount = next(n.get_editor_property("default_value") for n in L.get_material_expressions(mat)
                  if isinstance(n, u.MaterialExpressionScalarParameter) and str(n.get_editor_property("parameter_name"))=="TintAmount")
    if abs(amount-params["TintAmount"]) > 1e-4:
        raise RuntimeError("TintAmount did not stick on "+name)
    published[name] = mat.get_path_name()

pickup = u.load_asset("/Game/Characters/ModularOutfit20260924/Pickups/SM_FieldGloves_Pickup")
if pickup:
    slots = pickup.get_editor_property("static_materials")
    if slots:
        slots[0].set_editor_property("material_interface", u.load_asset(DEST+"/M_FieldGloves_Brown"))
        pickup.set_editor_property("static_materials", slots)
        save(pickup)

receipt = {
    "materials": published,
    "mapping": "triplanar 25cm + 60cm color; grain 0.36 mip 1.1; stronger wear/macro; black independent",
    "leather_tile_cm": 25,
    "leather_macro_tile_cm": 60,
    "leather_normal_strength": 0.36,
    "leather_normal_mip": 1.1,
    "leather_ao_amount": 0.30,
    "leather_cavity_amount": 0.18,
    "palm_grain_scale": 0.32,
    "wear_amount": 1.0,
    "glove_specular": 0.35,
    "spec_midpoint": 0.196,
    "black": {"ColorTint": [0.016, 0.018, 0.022], "LeatherNormalStrength": 0.30, "LeatherAOAmount": 0.16, "LeatherCavityAmount": 0.10},
    "hand_offsets": {"left": [0.37, 0.18, 0.11], "right": [0, 0, 0]},
    "shared_scan": [LEATHER+"/T_Fab_Leather_BaseColor", LEATHER+"/T_Fab_Leather_Roughness",
                     LEATHER+"/T_Fab_Leather_Normal", LEATHER+"/T_Fab_Leather_AO",
                     LEATHER+"/T_Fab_Leather_Cavity", LEATHER+"/T_Fab_Leather_Specular"],
    "authored": [TEX+"/T_FieldGloves_LeatherRegions", TEX+"/T_FieldGloves_StitchNormal",
                 TEX+"/T_FieldGloves_CuffField", TEX+"/T_FieldGloves_CuffRollNormal", TEX+"/T_FieldGloves_Wear"],
    "items": ["ue_field_gloves", "ue_field_gloves_black"],
    "runtime_tested": False,
}
(AUTHOR/"published.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
print("FIELD_GLOVES_LEATHER_PUBLISHED", json.dumps(receipt), flush=True)
