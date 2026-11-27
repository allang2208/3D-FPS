"""Import LumberMill-R49 Quixel Megascans (with Normandy/TemperateHills secondary style-calibration)
and Blender 5.1 3-room Lumber Mill architecture + hero props (with 100% resident PBR materials,
exact KBoxElem simple collisions, Nanite, and strict <=1024/512 texture-pool caps).
"""
import json
import math
import shutil
import sys
from pathlib import Path

import unreal as u

TOOLS = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/ForestVillage")
sys.path.insert(0, str(TOOLS))
import import_road_upgrade_r48 as r48_imp

lib = u.EditorAssetLibrary
ed = u.MaterialEditingLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
mesh_sub = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

LM_BASE = "/Game/ForestPathStudy/VillageRegion/LumberMill"
LM_ARCH = LM_BASE + "/Arch"
LM_RUINED = LM_BASE + "/Ruined"
LM_FAB = LM_BASE + "/Props"
LM_MATS = LM_BASE + "/Materials"

# Resident project PBR materials reused by Blender 3-room Lumber Mill & hero props (0 MiB extra Texture Pool!)
RESIDENT_MATS = {
    "Oak": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak",
    "OiledOak": "/Game/WorldGeneration/VillageTavern/Furniture/M_TavernOiledOak",
    "DarkWood": "/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelTimber",
    "Sawn": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterSawn",
    "Endgrain": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterCut",
    "Bark": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterBark",
    "Lime": "/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelLimewash",
    "Footing": "/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelFooting",
    "Stone": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_HearthStone",
    "Flagstone": "/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelFlagstone",
    "Slate": "/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelSlate",
    "ScaleIron": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor/Materials/M_SmithScaleIron",
    "Iron": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron",
    "Steel": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterSteel",
    "Brass": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterBrass",
    "Linen": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Linen",
    "Blanket": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Blanket",
    "Rope": "/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/Materials/M_StableWeatheredRope",
}

# Secondary color/saturation/roughness style calibration for Quixel scans whose native photo look
# differs slightly from our muted, warm-weathered Normandy TemperateHills wood/iron palette!
STYLE_TUNING = {
    # Bright industrial raw planks -> warm aged Normandy oak weathering + higher matte roughness
    "lumber_plank_stack": dict(tint=(0.76, 0.70, 0.61), desat=0.22, rough_mul=1.18),
    "lumber_planks":      dict(tint=(0.74, 0.68, 0.59), desat=0.20, rough_mul=1.15),
    "lumber_boards":      dict(tint=(0.86, 0.82, 0.76), desat=0.12, rough_mul=1.10),
    # Clean raw log piles -> slight woodland dampness & bark harmony with VillageCarpenter
    "lumber_logpile_s1":  dict(tint=(0.88, 0.85, 0.80), desat=0.10, rough_mul=1.08),
    "lumber_logpile_s2":  dict(tint=(0.88, 0.85, 0.80), desat=0.10, rough_mul=1.08),
    "lumber_firewood_pack": dict(tint=(0.86, 0.83, 0.78), desat=0.12, rough_mul=1.08),
    # Bright studio wooden bench/chair/shelf/ladder -> match VillageTavern oiled oak warmth!
    "prop_bench":         dict(tint=(0.78, 0.72, 0.64), desat=0.16, rough_mul=1.10),
    "prop_chair":         dict(tint=(0.76, 0.70, 0.62), desat=0.18, rough_mul=1.12),
    "prop_shelf":         dict(tint=(0.80, 0.74, 0.66), desat=0.14, rough_mul=1.10),
    "prop_ladder":        dict(tint=(0.80, 0.75, 0.67), desat=0.16, rough_mul=1.12),
    # Carts & wagons -> ground-dust weathered finish
    "prop_log_wagon":     dict(tint=(0.86, 0.83, 0.78), desat=0.12, rough_mul=1.08),
    "prop_hand_cart":     dict(tint=(0.86, 0.83, 0.78), desat=0.12, rough_mul=1.08),
    "prop_barrow":        dict(tint=(0.86, 0.83, 0.78), desat=0.12, rough_mul=1.08),
    # Tools, buckets, ropes, sacks -> authentic lived-in workshop patina
    "tool_axe":           dict(tint=(0.90, 0.88, 0.84), desat=0.10, rough_mul=1.05),
    "tool_bowsaw":        dict(tint=(0.88, 0.85, 0.80), desat=0.12, rough_mul=1.08),
    "tool_framesaw":      dict(tint=(0.86, 0.83, 0.78), desat=0.12, rough_mul=1.08),
    "tool_wedge":         dict(tint=(0.88, 0.86, 0.83), desat=0.10, rough_mul=1.05),
    "tool_handsaw":       dict(tint=(0.88, 0.86, 0.82), desat=0.10, rough_mul=1.05),
    "tool_hammer":        dict(tint=(0.90, 0.88, 0.85), desat=0.10, rough_mul=1.05),
    "prop_pulley":        dict(tint=(0.86, 0.82, 0.76), desat=0.14, rough_mul=1.08),
    "prop_rope":          dict(tint=(0.82, 0.78, 0.70), desat=0.16, rough_mul=1.12),
    "prop_bucket":        dict(tint=(0.86, 0.82, 0.76), desat=0.12, rough_mul=1.08),
    "prop_sack":          dict(tint=(0.82, 0.78, 0.70), desat=0.16, rough_mul=1.12),
}


def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError("Save failed: " + asset.get_path_name())


def ensure_lumber_prop_master():
    """Style-calibrated PBR parent for LumberMill Quixel props (Tint + Desaturate + RoughnessMul + PerInstanceRandom)."""
    path = f"{LM_MATS}/M_LumberPropScan"
    if lib.does_asset_exist(path):
        mat = u.load_asset(path)
        mat.set_editor_property("used_with_instanced_static_meshes", True)
        mat.set_editor_property("used_with_nanite", True)
        return mat
    lib.make_directory(LM_MATS)
    mat = tools.create_asset("M_LumberPropScan", LM_MATS, u.Material, u.MaterialFactoryNew())
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("used_with_nanite", True)

    b_node = ed.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D, -820, -220)
    b_node.set_editor_property("parameter_name", "B")
    b_node.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_COLOR)

    n_node = ed.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D, -820, 120)
    n_node.set_editor_property("parameter_name", "N")
    n_node.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_NORMAL)

    orm_node = ed.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D, -820, 420)
    orm_node.set_editor_property("parameter_name", "ORM")
    orm_node.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_MASKS)

    # Secondary Normandy palette calibration: Desaturate -> Tint -> PerInstanceRandom subtle variation
    desat_p = ed.create_material_expression(mat, u.MaterialExpressionScalarParameter, -600, -40)
    desat_p.set_editor_property("parameter_name", "Desaturate")
    desat_p.set_editor_property("default_value", 0.12)
    desat = ed.create_material_expression(mat, u.MaterialExpressionDesaturation, -460, -200)
    ed.connect_material_expressions(b_node, "RGB", desat, "")
    ed.connect_material_expressions(desat_p, "", desat, "Fraction")

    tint_p = ed.create_material_expression(mat, u.MaterialExpressionVectorParameter, -600, -420)
    tint_p.set_editor_property("parameter_name", "StyleTint")
    tint_p.set_editor_property("default_value", u.LinearColor(0.86, 0.82, 0.76, 1.0))

    rnd = ed.create_material_expression(mat, u.MaterialExpressionPerInstanceRandom, -600, -640)
    v_lo = ed.create_material_expression(mat, u.MaterialExpressionConstant, -600, -760)
    v_lo.set_editor_property("r", 0.90)
    v_hi = ed.create_material_expression(mat, u.MaterialExpressionConstant, -600, -840)
    v_hi.set_editor_property("r", 1.07)
    var_lerp = ed.create_material_expression(mat, u.MaterialExpressionLinearInterpolate, -420, -700)
    ed.connect_material_expressions(v_lo, "", var_lerp, "A")
    ed.connect_material_expressions(v_hi, "", var_lerp, "B")
    ed.connect_material_expressions(rnd, "", var_lerp, "Alpha")

    tint_mul = ed.create_material_expression(mat, u.MaterialExpressionMultiply, -280, -300)
    ed.connect_material_expressions(desat, "", tint_mul, "A")
    ed.connect_material_expressions(tint_p, "", tint_mul, "B")

    final_col = ed.create_material_expression(mat, u.MaterialExpressionMultiply, -120, -220)
    ed.connect_material_expressions(tint_mul, "", final_col, "A")
    ed.connect_material_expressions(var_lerp, "", final_col, "B")

    # Roughness multiplier clamped to [0.18..0.98] for realistic weathered wood/iron finish
    rmul_p = ed.create_material_expression(mat, u.MaterialExpressionScalarParameter, -600, 620)
    rmul_p.set_editor_property("parameter_name", "RoughnessMul")
    rmul_p.set_editor_property("default_value", 1.08)
    rmul = ed.create_material_expression(mat, u.MaterialExpressionMultiply, -380, 480)
    ed.connect_material_expressions(orm_node, "G", rmul, "A")
    ed.connect_material_expressions(rmul_p, "", rmul, "B")
    rclamp = ed.create_material_expression(mat, u.MaterialExpressionClamp, -200, 480)
    rclamp.set_editor_property("min_default", 0.18)
    rclamp.set_editor_property("max_default", 0.98)
    ed.connect_material_expressions(rmul, "", rclamp, "")

    ed.connect_material_property(final_col, "", u.MaterialProperty.MP_BASE_COLOR)
    ed.connect_material_property(n_node, "RGB", u.MaterialProperty.MP_NORMAL)
    ed.connect_material_property(orm_node, "R", u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    ed.connect_material_property(rclamp, "", u.MaterialProperty.MP_ROUGHNESS)
    ed.connect_material_property(orm_node, "B", u.MaterialProperty.MP_METALLIC)

    save(mat)
    return mat


WOODCHIP_DECAL_HLSL = r'''
struct FChipNoise
{
    float3 Hash(float2 p)
    {
        float3 v = frac(p.xyx * float3(.1031, .1030, .0973));
        v += dot(v, v.yxz + 33.33);
        return frac((v.xxy + v.yzz) * v.zyx);
    }
    float Noise(float2 p)
    {
        float2 i = floor(p), f = frac(p);
        f = f * f * (3. - 2. * f);
        return lerp(lerp(Hash(i).x, Hash(i + float2(1., 0.)).x, f.x),
                    lerp(Hash(i + float2(0., 1.)).x, Hash(i + 1.).x, f.x), f.y);
    }
    float Fbm(float2 p)
    {
        float a = 0.52 * Noise(p);
        a += 0.28 * Noise(p * 2.07 + float2(11.3, -7.1));
        a += 0.14 * Noise(p * 4.19 - float2(5.7, 13.9));
        a += 0.06 * Noise(p * 8.31 + float2(23.1, 4.7));
        return a;
    }
};

FChipNoise cn;
float2 w = P.xy * 0.01;
float2 dx = float2(0.01, 0.0), dy = float2(0.0, 0.01);
#if (PIXELSHADER || COMPUTESHADER) && !RAYHITGROUPSHADER
dx = ddx(w);
dy = ddy(w);
#endif

// 1) Multi-octave world-space domain warp + asymmetric drift lobes -> 100% NON-CIRCULAR organic scatter!
float2 d = UV * 2.0 - 1.0;
float2 warp1 = float2(cn.Fbm(w * 0.46 + float2(3.1, -2.4)), cn.Fbm(w * 0.46 + float2(17.4, -9.2))) - 0.5;
float2 warp2 = float2(cn.Fbm(w * 1.32 - float2(5.7, 4.1)), cn.Fbm(w * 1.32 + float2(-11.3, 8.6))) - 0.5;
float2 dWarp = d + warp1 * 0.78 + warp2 * 0.36;
float ang = atan2(dWarp.y, dWarp.x);
float lobe = (cn.Noise(float2(cos(ang) * 1.45 + w.x * 0.11, sin(ang) * 1.45 + w.y * 0.11)) - 0.5) * 0.52;
float rDist = length(dWarp) + lobe;
// Smooth containment strictly reaching 0.0 inside decal box edges (zero straight box clipping!)
float boxFade = 1.0 - smoothstep(0.64, 0.96, max(abs(d.x), abs(d.y)));
float clump = cn.Fbm(w * 0.92 + warp1 * 1.9) * 0.62 + cn.Fbm(w * 2.55 - warp2 * 1.3) * 0.38;
float baseCov = saturate((1.0 - smoothstep(0.14, 0.96, rDist)) * 1.24 + (clump - 0.50) * 0.72) * boxFade;

// 2) World-space non-repeating dual-rotated woodchip mulch sampling (zero UV stretch at any decal scale!)
float2 mUvA = w * 0.78 + warp1 * 0.12;
float2 mUvB = float2(w.x * 0.56 - w.y * 0.58, w.x * 0.58 + w.y * 0.56) * 1.12 + float2(0.37, 0.61);
float blendAB = smoothstep(0.32, 0.68, cn.Noise(w * 0.55 + 9.2));

float3 mColA = Texture2DSample(MulchB, MulchBSampler, mUvA).rgb;
float3 mColB = Texture2DSample(MulchB, MulchBSampler, mUvB).rgb;
float3 mColRaw = lerp(mColA, mColB, blendAB);

float3 mNrmA = UnpackNormalMap(Texture2DSample(MulchN, MulchNSampler, mUvA));
float3 mNrmB = UnpackNormalMap(Texture2DSample(MulchN, MulchNSampler, mUvB));
float3 mNrm = normalize(lerp(mNrmA, float3(mNrmB.x * 0.70 - mNrmB.y * 0.71, mNrmB.x * 0.71 + mNrmB.y * 0.70, mNrmB.z), blendAB));

float3 mOrmA = Texture2DSample(MulchORM, MulchORMSampler, mUvA).rgb;
float3 mOrmB = Texture2DSample(MulchORM, MulchORMSampler, mUvB).rgb;
float3 mOrm = lerp(mOrmA, mOrmB, blendAB);

// 3) Sample resident RoadMix DarkMud tile (0, 1) from Stony 2x2 atlas -> 100% color & micro-grain unity with yard mud!
const float span = 1984.0 / 2048.0;
float2 mudCoord = w * 0.50 + warp1 * 0.14;
float2 mudUv = (float2(0.0, 1.0) + 0.015625 + frac(mudCoord) * span) * 0.5;
float2 mudGx = dx * 0.50 * span * 0.5;
float2 mudGy = dy * 0.50 * span * 0.5;
float3 mudCol = Texture2DSampleGrad(StonyColor, GetMaterialSharedSampler(StonyColorSampler, Material.Clamp_WorldGroupSettings), mudUv, mudGx, mudGy).rgb;
float3 mudNrm = UnpackNormalMap(Texture2DSampleGrad(StonyNormal, GetMaterialSharedSampler(StonyNormalSampler, Material.Clamp_WorldGroupSettings), mudUv, mudGx, mudGy));
float3 mudArh = Texture2DSampleGrad(StonyARH, GetMaterialSharedSampler(StonyARHSampler, Material.Clamp_WorldGroupSettings), mudUv, mudGx, mudGy).rgb;

// 4) Individual chip height relief drives organic chip-by-chip fadeout & mud-in-crevices bleed!
float chipLuma = dot(mColRaw, float3(0.42, 0.39, 0.19));
float chipH = saturate(chipLuma * 1.45 + mOrm.r * 0.42 - 0.24);
// Warm weathered chestnut-oak woodchip tone harmonized directly with Normandy yard mud (not charcoal soot, not bright straw!)
float3 mDesat = lerp(mColRaw, chipLuma.xxx, 0.22);
float macroTone = lerp(0.86, 1.14, cn.Noise(w * 0.34 - 4.8));
float3 chipCol = mDesat * float3(0.38, 0.28, 0.19) * macroTone;
// Blend slight warm mud staining into low chip crevices so outer scattered flecks look pressed into wet earth!
float chipDominance = smoothstep(0.14, 0.74, baseCov * 1.12 + (chipH - 0.46) * 0.72);
float3 col = lerp(mudCol * 0.90, chipCol, lerp(0.32, 0.96, chipDominance));
float3 nrm = normalize(lerp(mudNrm, mNrm, lerp(0.35, 0.95, chipDominance)));
float rough = lerp(clamp(mudArh.g, 0.24, 0.96), clamp(mOrm.g * 1.06, 0.48, 0.94), chipDominance);

// 5) LIVE MPC_FPS_Weather ("WeatherWetness") Rain-Wetness & Glossy Mud-Crevice Sheen (matches forest_road_mix.ush 1:1!)
float wet = saturate(RainWetness);
float localMoist = saturate(0.16 * (1.0 - chipDominance) + wet * (0.58 + 0.38 * (1.0 - chipDominance)));
float dampTint = smoothstep(0.12, 0.78, localMoist);
col *= lerp(1.0, 0.62, dampTint);
rough = lerp(rough, lerp(0.20, 0.36, chipDominance), dampTint);
// Standing rainwater micro-sheen pooling in low hollows between woodchips under rain!
float puddleLevel = saturate(localMoist * 1.12 - 0.44 + (0.48 - chipH) * 0.68);
float puddle = smoothstep(0.10, 0.42, puddleLevel) * saturate(wet * 1.35);
[branch] if (puddle > 0.002)
{
    col = lerp(col, col * 0.68, puddle);
    nrm = normalize(lerp(nrm, float3(0.0, 0.0, 1.0), puddle * 0.88));
    rough = lerp(rough, lerp(0.10, 0.18, cn.Noise(w * 2.3)), puddle);
}

// 6) Final chip-by-chip organic opacity (high-relief chips scatter furthest; zero circular disc rim!)
float chipAlpha = smoothstep(0.08, 0.62, baseCov * 1.15 + (chipH - 0.48) * 0.58) * boxFade;
OutNormal = nrm;
OutRough = rough;
OutOpacity = saturate(chipAlpha * 0.96);
return col;
'''


def ensure_woodchip_decal_master(t_b, t_n, t_orm):
    """Build 3A Rain-Reactive Organic Ground Transition DeferredDecal material (M_LM_WoodchipDecal):
    - MD_DeferredDecal + BLEND_Translucent -> 100% conforms to micro-terrain with ZERO mesh lip!
    - Samples MPC_FPS_Weather (WeatherWetness) + resident RoadMix Stony mud atlas for 100% dry & rainy ground unity!
    - 4-octave world-space domain-warped FBM + individual chip height cutout -> ZERO circular disc rim!
    """
    m_path = f"{LM_MATS}/M_LM_WoodchipDecal"
    lib.make_directory(LM_MATS)
    mat = u.load_asset(m_path) if lib.does_asset_exist(m_path) else tools.create_asset(
        "M_LM_WoodchipDecal", LM_MATS, u.Material, u.MaterialFactoryNew()
    )
    ed.delete_all_material_expressions(mat)
    mat.set_editor_property("material_domain", u.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property("blend_mode", u.BlendMode.BLEND_TRANSLUCENT)

    def expr(cls):
        return ed.create_material_expression(mat, cls)

    def wire(a, pin, b, dst):
        if not ed.connect_material_expressions(a, pin, b, dst):
            raise RuntimeError(f"M_LM_WoodchipDecal: cannot connect {pin} -> {dst}")

    custom = expr(u.MaterialExpressionCustom)
    custom.set_editor_property("desc", "LM_WoodchipDecal_R49c")
    custom.set_editor_property("output_type", u.CustomMaterialOutputType.CMOT_FLOAT3)
    custom.set_editor_property("code", WOODCHIP_DECAL_HLSL)

    in_names = (
        "P", "UV", "RainWetness",
        "MulchB", "MulchN", "MulchORM",
        "StonyColor", "StonyNormal", "StonyARH",
    )
    pins = []
    for nm in in_names:
        p = u.CustomInput()
        p.set_editor_property("input_name", nm)
        pins.append(p)
    custom.set_editor_property("inputs", pins)

    outs = []
    for oname, okind in (("OutNormal", "FLOAT3"), ("OutRough", "FLOAT1"), ("OutOpacity", "FLOAT1")):
        o = u.CustomOutput()
        o.set_editor_property("output_name", oname)
        o.set_editor_property("output_type", getattr(u.CustomMaterialOutputType, "CMOT_" + okind))
        outs.append(o)
    custom.set_editor_property("additional_outputs", outs)

    wire(expr(u.MaterialExpressionWorldPosition), "", custom, "P")
    wire(expr(u.MaterialExpressionTextureCoordinate), "", custom, "UV")

    rain = expr(u.MaterialExpressionCollectionParameter)
    rain.set_editor_property("collection", u.load_asset("/Game/Weather/Materials/MPC_FPS_Weather"))
    rain.set_editor_property("parameter_name", "WeatherWetness")
    wire(rain, "", custom, "RainWetness")

    road_mix_dir = "/Game/ForestPathStudy/VillageRegion/Reference/GateRoad/RoadMix"
    tex_bindings = (
        ("MulchB", t_b, "COLOR"),
        ("MulchN", t_n, "NORMAL"),
        ("MulchORM", t_orm, "MASKS"),
        ("StonyColor", u.load_asset(f"{road_mix_dir}/T_StonyColor"), "COLOR"),
        ("StonyNormal", u.load_asset(f"{road_mix_dir}/T_StonyNormal"), "NORMAL"),
        ("StonyARH", u.load_asset(f"{road_mix_dir}/T_StonyARH"), "MASKS"),
    )
    for tpin, tobj_tex, smode in tex_bindings:
        if not tobj_tex:
            raise RuntimeError(f"M_LM_WoodchipDecal: missing texture for {tpin}")
        tn = expr(u.MaterialExpressionTextureObject)
        tn.set_editor_property("texture", tobj_tex)
        tn.set_editor_property("sampler_type", getattr(u.MaterialSamplerType, "SAMPLERTYPE_" + smode))
        wire(tn, "", custom, tpin)

    ed.connect_material_property(custom, "", u.MaterialProperty.MP_BASE_COLOR)
    ed.connect_material_property(custom, "OutNormal", u.MaterialProperty.MP_NORMAL)
    ed.connect_material_property(custom, "OutRough", u.MaterialProperty.MP_ROUGHNESS)
    ed.connect_material_property(custom, "OutOpacity", u.MaterialProperty.MP_OPACITY)

    ed.layout_material_expressions(mat)
    errs = ed.recompile_material(mat)
    if errs:
        raise RuntimeError(f"M_LM_WoodchipDecal compile failed: {errs}")
    save(mat)
    return mat


def build_mulch_material(r49_src: Path, master):
    """Ensure Woodchip/Bark Mulch textures (1024 B / 512 N / 512 ORM) and compile 3A Rain-Reactive M_LM_WoodchipDecal."""
    mulch_uid = "f8f77f90-28d4-4d2e-9495-fd3a437f9b56"
    raw = r49_src / "Fab" / mulch_uid
    tex_dir = f"{LM_MATS}/MulchTex"
    lib.make_directory(tex_dir)

    b_file = r48_imp.find_tex_file(raw, ["_BaseColor.jpg", "_BaseColor.png", "_B.png"])
    n_file = r48_imp.find_tex_file(raw, ["_Normal.jpg", "_Normal.png", "_N.png"])
    r_file = r48_imp.find_tex_file(raw, ["_Roughness.jpg", "_Roughness.png"])
    ao_file = r48_imp.find_tex_file(raw, ["_AO.jpg", "_AO.png"])

    orm_png = raw / "T_LM_Mulch_ORM.png"
    if not orm_png.is_file() and r_file and ao_file:
        import subprocess
        py = shutil.which("py") or "python"
        code = (
            "from PIL import Image; import numpy as np;"
            f"ao=Image.open(r'{ao_file}').convert('L').resize((512,512));"
            f"rg=Image.open(r'{r_file}').convert('L').resize((512,512));"
            "mt=Image.new('L',(512,512),0);"
            f"Image.merge('RGB',(ao,rg,mt)).save(r'{orm_png}')"
        )
        subprocess.run([py, "-3.11", "-c", code], check=True)

    t_b = u.load_asset(f"{tex_dir}/T_LM_Mulch_B") if lib.does_asset_exist(f"{tex_dir}/T_LM_Mulch_B") else r48_imp.import_tex(b_file, tex_dir, "T_LM_Mulch_B", "DEFAULT", True, 1024)
    t_n = u.load_asset(f"{tex_dir}/T_LM_Mulch_N") if lib.does_asset_exist(f"{tex_dir}/T_LM_Mulch_N") else r48_imp.import_tex(n_file, tex_dir, "T_LM_Mulch_N", "NORMALMAP", False, 512)
    t_orm = u.load_asset(f"{tex_dir}/T_LM_Mulch_ORM") if lib.does_asset_exist(f"{tex_dir}/T_LM_Mulch_ORM") else r48_imp.import_tex(orm_png, tex_dir, "T_LM_Mulch_ORM", "MASKS", False, 512)

    r48_imp.bind_master_defaults(master, {"B": t_b, "N": t_n, "ORM": t_orm})

    # Clean up obsolete R49b mesh-based mulch materials
    for obs in (f"{LM_MATS}/MI_LM_WoodchipMulch", f"{LM_MATS}/M_LM_WoodchipMulch"):
        if lib.does_asset_exist(obs):
            lib.delete_asset(obs)

    decal_mat = ensure_woodchip_decal_master(t_b, t_n, t_orm)
    return decal_mat


def configure_nanite_and_simple_collision(mesh, colliders=None, is_hero_arch=False, keep_tri_pct=None, enable_nanite=True):
    """Apply exact simple box colliders (KBoxElem) + UE 5.8 GeometryScript collision cook
    + CTF_USE_SIMPLE_AS_COMPLEX + Nanite (100% lossless architectural fallback for hero buildings, 35% fallback for organic scans!).
    """
    mesh.modify()
    if colliders is not None:
        mesh_sub.remove_collisions(mesh)
        if len(colliders) > 0:
            body = mesh.get_editor_property("body_setup")
            if body is None:
                mesh_sub.add_simple_collisions(mesh, u.ScriptingCollisionShapeType.BOX)
                body = mesh.get_editor_property("body_setup")
                mesh_sub.remove_collisions(mesh)
            agg = body.get_editor_property("agg_geom")
            boxes = []
            for col in colliders:
                box = u.KBoxElem()
                c = col["center"]
                s = col["size"]
                box.set_editor_property("center", u.Vector(float(c[0]), float(c[1]), float(c[2])))
                box.set_editor_property("x", float(s[0]))
                box.set_editor_property("y", float(s[1]))
                box.set_editor_property("z", float(s[2]))
                yaw = float(col.get("yaw", 0.0))
                if abs(yaw) > 0.01:
                    box.set_editor_property("rotation", u.Rotator(pitch=0.0, yaw=yaw, roll=0.0))
                boxes.append(box)
            agg.set_editor_property("box_elems", boxes)
            body.set_editor_property("agg_geom", agg)
            body.set_editor_property("collision_trace_flag", u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
            mesh.set_editor_property("body_setup", body)
            # Mandatory UE 5.8 GeometryScript collision cook so Chaos runtime uses exact KBoxElem geometry!
            cooked = u.GeometryScript_Collision.get_simple_collision_from_static_mesh(mesh)
            u.GeometryScript_Collision.set_simple_collision_of_static_mesh(
                cooked, mesh, u.GeometryScriptSetSimpleCollisionOptions()
            )
            body = mesh.get_editor_property("body_setup")
            actual = len(body.get_editor_property("agg_geom").get_editor_property("box_elems"))
            if actual != len(colliders):
                raise RuntimeError(f"Collision cook mismatch on {mesh.get_name()}: expected {len(colliders)}, got {actual}")
    else:
        if mesh_sub.get_simple_collision_count(mesh) == 0:
            mesh_sub.add_simple_collisions(mesh, u.ScriptingCollisionShapeType.BOX)
        body = mesh.get_editor_property("body_setup")
        if body:
            body.set_editor_property("collision_trace_flag", u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)

    if not enable_nanite:
        ns = mesh.get_editor_property("nanite_settings")
        ns.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", ns)
        body = mesh.get_editor_property("body_setup")
        if body:
            body.set_editor_property("collision_trace_flag", u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        save(mesh)
        return

    if keep_tri_pct is not None and not is_hero_arch:
        ns = mesh.get_editor_property("nanite_settings")
        if hasattr(ns, "keep_percent_triangles"):
            ns.set_editor_property("keep_percent_triangles", float(keep_tri_pct))
            mesh.set_editor_property("nanite_settings", ns)

    # CRITICAL FIX: For sharp architectural hero buildings (is_hero_arch=True), enable preserve_area=True
    # and temporarily set CTF_USE_DEFAULT during BuildSceneryNaniteMesh so FallbackPercentTriangles stays 1.0
    # (zero shredded walls/stairs/mullions in Lumen, VSM, reflections, and captures!), then restore CTF_USE_SIMPLE_AS_COMPLEX!
    body = mesh.get_editor_property("body_setup")
    if is_hero_arch and body is not None:
        ns = mesh.get_editor_property("nanite_settings")
        ns.set_editor_property("fallback_percent_triangles", 1.0)
        ns.set_editor_property("fallback_relative_error", 0.0)
        if hasattr(ns, "preserve_area"):
            ns.set_editor_property("preserve_area", True)
        mesh.set_editor_property("nanite_settings", ns)
        body.set_editor_property("collision_trace_flag", u.CollisionTraceFlag.CTF_USE_DEFAULT)
        mesh.set_editor_property("body_setup", body)

    ok_nanite = u.ForestVillageRegion.build_scenery_nanite_mesh(mesh, None)
    if not ok_nanite:
        ns = mesh.get_editor_property("nanite_settings")
        ns.set_editor_property("enabled", True)
        mesh.set_editor_property("nanite_settings", ns)

    # Restore CTF_USE_SIMPLE_AS_COMPLEX for cheap exact KBoxElem Chaos collision!
    body = mesh.get_editor_property("body_setup")
    if body is not None:
        body.set_editor_property("collision_trace_flag", u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        mesh.set_editor_property("body_setup", body)
    save(mesh)


def import_blender_architecture(r49_src: Path, decal_mat):
    """Import all 16 Blender 5.1 FBX meshes with resident PBR materials, cooked KBoxElem colliders, and smart Nanite/LODs."""
    fbx_dir = r49_src / "ArchFBX"
    manifest = json.loads((fbx_dir / "arch-manifest.json").read_text(encoding="utf-8"))
    lib.make_directory(LM_ARCH)
    # Remove obsolete R49/R49b meshes replaced in R49c
    for obs_nm in ("SM_LM_Signboard", "SM_LM_ChoppingStation", "SM_LM_MulchPatch"):
        obs_p = f"{LM_ARCH}/{obs_nm}"
        if lib.does_asset_exist(obs_p):
            lib.delete_asset(obs_p)
    mat_cache = {}
    for key, mpath in RESIDENT_MATS.items():
        m = u.load_asset(mpath)
        if not m:
            raise RuntimeError(f"Missing resident material {key}: {mpath}")
        # If a resident Material lacks used_with_nanite, duplicate it locally under LumberMill/Materials (0 extra textures, 0 runtime PSO hitch!)
        if isinstance(m, u.Material) and not bool(m.get_editor_property("used_with_nanite")):
            local_mpath = f"{LM_MATS}/M_LM_Res_{key}"
            if not lib.does_asset_exist(local_mpath):
                lib.duplicate_asset(mpath, local_mpath)
            lm = u.load_asset(local_mpath)
            lm.set_editor_property("used_with_nanite", True)
            lm.set_editor_property("used_with_instanced_static_meshes", True)
            ed.recompile_material(lm)
            save(lm)
            m = lm
            print(f"[MAT-NANITE] Cloned local Nanite-ready {local_mpath} (0 extra textures)")
        mat_cache[key] = m

    # Smart Nanite + Auto-LOD policy:
    # - Keep multi-island architectural shells & thin-plank/saw-tooth craft props non-Nanite + auto-LODs
    #   (ZERO Nanite coarse root-page board shredding + leaner Always-Resident Nanite memory!)
    # - Keep ALL sculpted organic stumps, sawbuck, bark chip scatters, camp fences & gate arch Nanite-enabled!
    NON_NANITE_ARCH = {
        "SM_LM_Warehouse", "SM_LM_ToolRoom", "SM_LM_Bunkhouse",
        "SM_LM_TimberRack", "SM_LM_BunkBed",
        "SM_LM_ChoppingStumpA", "SM_LM_ChoppingStumpB",
        "SM_LM_TwoManCrosscutSaw", "SM_LM_FramePitSaw", "SM_LM_WorkbenchSawSet",
    }

    imported = {}
    for entry in manifest:
        name = entry["name"]
        fbx_path = Path(entry["lods"][0]["file"])
        dest_asset = f"{LM_ARCH}/{name}"

        opts = u.FbxImportUI()
        opts.import_mesh = True
        opts.import_as_skeletal = False
        opts.import_materials = False
        opts.import_textures = False
        opts.automated_import_should_detect_type = False
        opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        sm_data = opts.static_mesh_import_data
        sm_data.combine_meshes = True
        sm_data.auto_generate_collision = False
        sm_data.generate_lightmap_u_vs = False
        sm_data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
        sm_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        sm_data.import_uniform_scale = 1.0

        task = u.AssetImportTask()
        task.filename = str(fbx_path)
        task.destination_path = LM_ARCH
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.options = opts
        tools.import_asset_tasks([task])

        mesh = u.load_asset(dest_asset)
        if not isinstance(mesh, u.StaticMesh):
            raise RuntimeError(f"Failed importing Blender FBX {name}")

        # Assign resident PBR materials matching exact slot names
        slots = list(mesh.get_editor_property("static_materials"))
        for idx, slot in enumerate(slots):
            sname = str(slot.get_editor_property("imported_material_slot_name") or slot.get_editor_property("material_slot_name"))
            base_key = sname.split(".")[0]
            mat = mat_cache.get(base_key) or mat_cache.get("Oak")
            mesh.set_material(idx, mat)

        is_scatter = name.startswith("SM_LM_BarkChipScatter")
        use_nanite = name not in NON_NANITE_ARCH
        configure_nanite_and_simple_collision(
            mesh,
            colliders=[] if is_scatter else entry["colliders"],
            is_hero_arch=not is_scatter,
            enable_nanite=use_nanite,
        )
        # Generate clean 3-level LODs on non-Nanite interior craft props for low distant triangle cost!
        if not use_nanite and name not in ("SM_LM_Warehouse", "SM_LM_ToolRoom", "SM_LM_Bunkhouse"):
            try:
                lod_opts = u.StaticMeshReductionOptions()
                r0 = u.StaticMeshReductionSettings(); r0.percent_triangles = 1.0; r0.screen_size = 1.0
                r1 = u.StaticMeshReductionSettings(); r1.percent_triangles = 0.55; r1.screen_size = 0.25
                r2 = u.StaticMeshReductionSettings(); r2.percent_triangles = 0.28; r2.screen_size = 0.08
                lod_opts.reduction_settings = [r0, r1, r2]
                lod_opts.auto_compute_lod_screen_size = False
                mesh_sub.set_lods(mesh, lod_opts)
                save(mesh)
            except Exception as ex:
                print(f"[LOD-WARN] {name}: {ex}")
        box = mesh.get_bounding_box()
        sz = box.max - box.min
        imported[name] = {
            "mesh": mesh.get_path_name(),
            "size_cm": [round(float(sz.x), 1), round(float(sz.y), 1), round(float(sz.z), 1)],
            "min_cm": [round(float(box.min.x), 1), round(float(box.min.y), 1), round(float(box.min.z), 1)],
            "max_cm": [round(float(box.max.x), 1), round(float(box.max.y), 1), round(float(box.max.z), 1)],
            "colliders": len(entry["colliders"]),
            "nanite": bool(mesh.get_editor_property("nanite_settings").enabled),
        }
        print(f"[ARCH-UE] {name:24s} | size={imported[name]['size_cm']} | col={imported[name]['colliders']} | nanite={imported[name]['nanite']}")
    return imported


def import_quixel_lumber_props(r49_src: Path, master):
    """Import all 23 Quixel 3D lumber/logging props with secondary Normandy style calibration,
    strict <=1024 B / 512 N / 512 ORM texture caps, Nanite, and simple box collisions!
    """
    manifest = json.loads((r49_src / "fab-manifest.json").read_text(encoding="utf-8"))
    stage_root = r49_src / "StagedGLTF"
    lib.make_directory(LM_FAB)
    catalog = {}

    # Skip multi-part 100x-scaled glTF farm vehicles (resident SM_Stable_HayWagon & SM_MillBarrow already match 1:1!)
    skip_roles = {"prop_log_wagon", "prop_hand_cart", "prop_barrow"}
    for item in manifest["acquired"]:
        if item["format"] == "texture-set" or item["role"] in skip_roles:
            continue
        role = item["role"]
        uid = item["listing"]
        raw_dir = r49_src / "Fab" / uid
        gltf_files = list(raw_dir.glob("*.gltf"))
        if not gltf_files:
            continue
        stem = gltf_files[0].stem
        key = stem.split("_")[0]
        dest_dir = f"{LM_FAB}/{role}_{key}"
        lib.make_directory(dest_dir)

        b_file = r48_imp.find_tex_file(raw_dir, ["_B.png", "_BaseColor.jpg", "_BaseColor.png"])
        n_file = r48_imp.find_tex_file(raw_dir, ["_N.png", "_Normal.jpg", "_Normal.png"])
        orm_file = r48_imp.find_tex_file(raw_dir, ["_ORM.png", "_ORDp.png"])
        if not (b_file and n_file and orm_file):
            raise RuntimeError(f"Missing PBR maps for {role} ({uid}) in {raw_dir}")

        # Strict R49b VRAM discipline: ONLY 3 large hero log/plank piles get 1024/512/512; ALL medium/small props get 512/512/256!
        is_large_hero = role in ("lumber_plank_stack", "lumber_logpile_s1", "lumber_logpile_s2")
        cap_b = 1024 if is_large_hero else 512
        cap_n = 512
        cap_orm = 512 if is_large_hero else 256

        def ensure_tex_cap(src_file, tname, comp_mode, srgb, cap):
            tpath = f"{dest_dir}/{tname}"
            if lib.does_asset_exist(tpath):
                t = u.load_asset(tpath)
                if isinstance(t, u.Texture2D):
                    changed = False
                    if int(t.get_editor_property("max_texture_size")) != cap:
                        t.set_editor_property("max_texture_size", cap)
                        changed = True
                    if bool(t.get_editor_property("never_stream")):
                        t.set_editor_property("never_stream", False)
                        changed = True
                    if changed:
                        save(t)
                    return t
            return r48_imp.import_tex(src_file, dest_dir, tname, comp_mode, srgb, cap)

        t_b = ensure_tex_cap(b_file, f"T_{key}_B", "DEFAULT", True, cap_b)
        t_n = ensure_tex_cap(n_file, f"T_{key}_N", "NORMALMAP", False, cap_n)
        t_orm = ensure_tex_cap(orm_file, f"T_{key}_ORM", "MASKS", False, cap_orm)

        # Style-calibrated MaterialInstanceConstant
        mi_name = f"MI_{role}_{key}"
        mi_path = f"{dest_dir}/{mi_name}"
        mi = u.load_asset(mi_path) if lib.does_asset_exist(mi_path) else tools.create_asset(
            mi_name, dest_dir, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew()
        )
        mi.set_editor_property("parent", master)
        ed.set_material_instance_texture_parameter_value(mi, "B", t_b)
        ed.set_material_instance_texture_parameter_value(mi, "N", t_n)
        ed.set_material_instance_texture_parameter_value(mi, "ORM", t_orm)
        tune = STYLE_TUNING.get(role, dict(tint=(0.86, 0.83, 0.78), desat=0.12, rough_mul=1.08))
        ed.set_material_instance_vector_parameter_value(mi, "StyleTint", u.LinearColor(*tune["tint"], 1.0))
        ed.set_material_instance_scalar_parameter_value(mi, "Desaturate", float(tune["desat"]))
        ed.set_material_instance_scalar_parameter_value(mi, "RoughnessMul", float(tune["rough_mul"]))
        ed.update_material_instance(mi)
        save(mi)

        # Stage clean glTF (strip embedded materials, keep 1 hero variant for multi-part sets or up to 2 for boards)
        max_v = 2 if role in ("lumber_boards", "lumber_firewood_pack") else 1
        staged_gltf, gstem = r48_imp.stage_clean_gltf(raw_dir, stage_root / f"{role}_{key}", max_variants=max_v)
        sm_dir = f"{dest_dir}/SM_{gstem}"
        existing = [
            u.load_asset(p) for p in lib.list_assets(sm_dir, recursive=True, include_folder=False)
            if isinstance(u.load_asset(p), u.StaticMesh) and "billboard" not in p.lower()
        ] if lib.does_directory_exist(sm_dir) else []
        if not existing:
            imported_objs = r48_imp.import_file(staged_gltf, dest_dir, f"SM_{gstem}")
            existing = [o for o in imported_objs if isinstance(o, u.StaticMesh) and "billboard" not in o.get_name().lower()]
        if not existing:
            raise RuntimeError(f"No StaticMesh imported for {role} ({uid})")

        meshes_out = []
        keep_pct = 0.70 if is_large_hero else 0.55
        for sm in existing:
            for si in range(len(sm.get_editor_property("static_materials"))):
                sm.set_material(si, mi)
            # Only rebuild if Nanite isn't enabled or simple collision missing (keeps R49b compound iteration super fast!)
            ns = sm.get_editor_property("nanite_settings")
            body = sm.get_editor_property("body_setup")
            need_cfg = (not bool(ns.enabled)) or (mesh_sub.get_simple_collision_count(sm) == 0) or (
                body and body.get_editor_property("collision_trace_flag") != u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX
            )
            if need_cfg:
                configure_nanite_and_simple_collision(sm, colliders=None, is_hero_arch=False, keep_tri_pct=keep_pct)
            box = sm.get_bounding_box()
            sz = box.max - box.min
            meshes_out.append({
                "mesh": sm.get_path_name(),
                "size_cm": [round(float(sz.x), 1), round(float(sz.y), 1), round(float(sz.z), 1)],
                "min_cm": [round(float(box.min.x), 1), round(float(box.min.y), 1), round(float(box.min.z), 1)],
                "max_cm": [round(float(box.max.x), 1), round(float(box.max.y), 1), round(float(box.max.z), 1)],
                "nanite": bool(sm.get_editor_property("nanite_settings").enabled),
            })
        catalog[role] = {
            "uid": uid,
            "title": item["title"],
            "material": mi.get_path_name(),
            "caps": [cap_b, cap_n, cap_orm],
            "meshes": meshes_out,
        }
        print(f"[FAB-UE] {role:22s} | n={len(meshes_out)} | sz0={meshes_out[0]['size_cm']} | caps={catalog[role]['caps']}")
    return catalog


def import_blender_ruined(r49_src: Path):
    """Import all 8 Blender 5.1 Ruined Lumber Mill FBX meshes (0 extra textures, resident PBR materials, smart LOD/Nanite)."""
    fbx_dir = r49_src / "RuinedFBX"
    manifest_path = fbx_dir / "ruined-manifest.json"
    if not manifest_path.is_file():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lib.make_directory(LM_RUINED)

    mat_cache = {}
    for key, mpath in RESIDENT_MATS.items():
        local_mpath = f"{LM_MATS}/M_LM_Res_{key}"
        m = u.load_asset(local_mpath) if lib.does_asset_exist(local_mpath) else u.load_asset(mpath)
        if not m:
            raise RuntimeError(f"Missing resident material {key}: {mpath}")
        mat_cache[key] = m

    NON_NANITE_RUINED = {
        "SM_LM_Warehouse_Ruined", "SM_LM_ToolRoom_Ruined", "SM_LM_Bunkhouse_Ruined",
        "SM_LM_TimberRack_Ruined",
    }

    imported = {}
    for entry in manifest:
        name = entry["name"]
        fbx_path = Path(entry["lods"][0]["file"])
        dest_asset = f"{LM_RUINED}/{name}"

        opts = u.FbxImportUI()
        opts.import_mesh = True
        opts.import_as_skeletal = False
        opts.import_materials = False
        opts.import_textures = False
        opts.automated_import_should_detect_type = False
        opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        sm_data = opts.static_mesh_import_data
        sm_data.combine_meshes = True
        sm_data.auto_generate_collision = False
        sm_data.generate_lightmap_u_vs = False
        sm_data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
        sm_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        sm_data.import_uniform_scale = 1.0

        task = u.AssetImportTask()
        task.filename = str(fbx_path)
        task.destination_path = LM_RUINED
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.options = opts
        tools.import_asset_tasks([task])

        mesh = u.load_asset(dest_asset)
        if not isinstance(mesh, u.StaticMesh):
            raise RuntimeError(f"Failed importing Ruined Blender FBX {name}")

        slots = list(mesh.get_editor_property("static_materials"))
        for idx, slot in enumerate(slots):
            sname = str(slot.get_editor_property("imported_material_slot_name") or slot.get_editor_property("material_slot_name"))
            base_key = sname.split(".")[0]
            mesh.set_material(idx, mat_cache.get(base_key) or mat_cache.get("DarkWood"))

        use_nanite = name not in NON_NANITE_RUINED
        configure_nanite_and_simple_collision(
            mesh,
            colliders=entry["colliders"],
            is_hero_arch=True,
            enable_nanite=use_nanite,
        )
        if not use_nanite:
            try:
                lod_opts = u.StaticMeshReductionOptions()
                r0 = u.StaticMeshReductionSettings(); r0.percent_triangles = 1.0; r0.screen_size = 1.0
                r1 = u.StaticMeshReductionSettings(); r1.percent_triangles = 0.55; r1.screen_size = 0.25
                r2 = u.StaticMeshReductionSettings(); r2.percent_triangles = 0.28; r2.screen_size = 0.08
                lod_opts.reduction_settings = [r0, r1, r2]
                lod_opts.auto_compute_lod_screen_size = False
                mesh_sub.set_lods(mesh, lod_opts)
                save(mesh)
            except Exception as ex:
                print(f"[LOD-WARN] {name}: {ex}")

        box = mesh.get_bounding_box()
        sz = box.max - box.min
        imported[name] = {
            "mesh": mesh.get_path_name(),
            "size_cm": [round(float(sz.x), 1), round(float(sz.y), 1), round(float(sz.z), 1)],
            "min_cm": [round(float(box.min.x), 1), round(float(box.min.y), 1), round(float(box.min.z), 1)],
            "max_cm": [round(float(box.max.x), 1), round(float(box.max.y), 1), round(float(box.max.z), 1)],
            "colliders": len(entry["colliders"]),
            "nanite": bool(mesh.get_editor_property("nanite_settings").enabled),
        }
        print(f"[RUIN-UE] {name:28s} | size={imported[name]['size_cm']} | col={imported[name]['colliders']} | nanite={imported[name]['nanite']}")
    return imported


def import_all(r49_src: Path):
    master = ensure_lumber_prop_master()
    mulch_mi = build_mulch_material(r49_src, master)
    arch = import_blender_architecture(r49_src, mulch_mi)
    ruined = import_blender_ruined(r49_src)
    props = import_quixel_lumber_props(r49_src, master)
    out = {"arch": arch, "ruined": ruined, "props": props}
    (r49_src / "lumber-asset-catalog.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"LUMBER_IMPORT_OK: {len(arch)} Blender arch/hero + {len(ruined)} Ruined + {len(props)} Quixel prop roles")
    return out
