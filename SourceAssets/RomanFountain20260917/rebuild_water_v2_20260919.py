"""水体 v12：修掉"水面/水帘/泡沫全 flat"的单一根因并重挂溢流几何。

根因（2026-09-19 隔离拍证实）：四个水材质把 `MaterialExpressionObjectPositionWS` 当位置输入——
该节点输出**物体原点（每物体常量）**而非逐像素位置 → 波高场/法线/柱面 UV 全部在常量点求值：
水面整体刚性升降（看不见）、法线均匀倾斜（无变化）、水帘条纹采样单一 texel（平板）、
泡沫/焦散采样单一 texel（不可见）。v5–v10 六轮调参因此全部无效。

修法：
1. 新建四个 *V2 材质，位置输入 = WorldPosition − ObjectPositionWS（逐像素、随摆放平移不变）；
   参数名与旧材质一致，MIC 换父级后旧覆盖项继续生效。
2. MIC 换父级（Foam/Wet→FilmV2，CascadeFlow→CascadeFlowV2，Caustics→CausticsOverlayV2，
   WaveWater→WaveWaterV2）——网格槽位指向 MIC 不变，无需改网格槽/C++/关卡。
3. 溢流水帘几何重挂：旧水帘半径埋在碗外鼓包**里面**（只露出穿墙的暗矩形）；V2 水帘挂在
   外鼓包之外（离唇抛物线下垂），湿痕带/水线泡沫环收进碗内壁。原地覆盖 SM_RomanFountain_WaterFX
   （同名资产 → 所有引用自动生效）。
4. MIC 参数按"小波幅+高频细节+强白沫"重调。
全程不删任何被引用材质的表达式表（!IsRooted 断言坑）；只新建资产 + 换父级 + 覆盖网格。
"""

import os
import time
import unreal

DIR = "/Game/Props/RomanFountain20260917"
MATDIR = DIR + "/Materials"
FILM = MATDIR + "/M_FountainWaterFilmV2"
CASCADE = MATDIR + "/M_FountainCascadeFlowV2"
CAUSTICS = MATDIR + "/M_FountainCausticsOverlayV2"
WAVE = MATDIR + "/M_FountainWaveWaterV2"
FX_MESH = DIR + "/SM_RomanFountain_WaterFX"

PACK = "/Game/WaterMaterials"
T_FOAM_EDGE = PACK + "/Textures/T_Ocean_EdgeFoam"
T_FOAM_FALL = PACK + "/Textures/T_Waterfall_Foam_Directional"
T_CAUSTICS = PACK + "/Textures/T_Caustics"
CUBEMAP = PACK + "/Textures/T_Cubemap"
NOISE_CANDIDATES = (PACK + "/Textures/T_Noises", PACK + "/Textures/T_Noise_Progressive",
                    PACK + "/Textures/T_Noise_Curves", T_FOAM_EDGE)
T_NOISE = next((p for p in NOISE_CANDIDATES if unreal.load_asset(p)), NOISE_CANDIDATES[0])

SCALE = 2.0
STARTED = time.time()
LOG = []
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
SV = getattr(unreal, "ModelingService", None)


def log(m):
    print("[wv2] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-34s %s" % (label, "OK" if ok else "FAIL"))
    return bool(ok)


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


def save_fresh(asset, path, label):
    EAL.save_loaded_asset(asset, True)
    for _ in range(10):
        stamp = disk(path)
        if stamp and stamp[2] >= STARTED - 120.0:
            log("saved %-30s %s" % (label, stamp))
            return stamp
        time.sleep(1.0)
        EAL.save_loaded_asset(asset, True)
    log("saved %-30s STALE %s" % (label, disk(path)))
    return disk(path)


def ensure(path):
    a = EAL.load_asset(path) or unreal.load_asset(path)
    if a:
        return a
    folder, name = path.rsplit("/", 1)
    EAL.make_directory(folder)
    return TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())


def ex(mat, cls):
    return MEL.create_material_expression(mat, cls)


def scalar(mat, name, value):
    n = ex(mat, unreal.MaterialExpressionScalarParameter)
    n.set_editor_property("parameter_name", name)
    n.set_editor_property("default_value", value)
    return n


def vector(mat, name, value):
    n = ex(mat, unreal.MaterialExpressionVectorParameter)
    n.set_editor_property("parameter_name", name)
    n.set_editor_property("default_value", value)
    return n


def texture_param(mat, name, tex_path):
    n = ex(mat, unreal.MaterialExpressionTextureSampleParameter2D)
    n.set_editor_property("parameter_name", name)
    tex = unreal.load_asset(tex_path)
    if tex:
        n.set_editor_property("texture", tex)
    return n


def cube_param(mat, name, tex_path):
    n = ex(mat, unreal.MaterialExpressionTextureSampleParameterCube)
    n.set_editor_property("parameter_name", name)
    tex = unreal.load_asset(tex_path)
    if tex:
        n.set_editor_property("texture", tex)
    return n


def custom(mat, code, inputs, output_type=None, input_types=None):
    n = ex(mat, unreal.MaterialExpressionCustom)
    if output_type is not None:
        n.set_editor_property("output_type", output_type)
    n.set_editor_property("code", code)
    pins = []
    for pin_name in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", pin_name)
        if input_types and pin_name in input_types:
            try:
                pin.set_editor_property("input_type", input_types[pin_name])
            except Exception:
                pass  # 5.8 的 FCustomInput 没有 input_type：类型跟接入的表达式走
        pins.append(pin)
    n.set_editor_property("inputs", pins)
    for pin_name, source in inputs.items():
        MEL.connect_material_expressions(source, "", n, pin_name)
    return n


def link(from_node, to_node, to_pin, from_pin=""):
    ok = MEL.connect_material_expressions(from_node, from_pin, to_node, to_pin)
    if not ok:
        log("CONNECT FAIL %s -> %s.%s" % (from_node.get_class().get_name(),
                                          to_node.get_class().get_name(), to_pin))
    return ok


def link_any(from_node, to_node, pins, from_pin=""):
    for p in pins:
        if MEL.connect_material_expressions(from_node, from_pin, to_node, p):
            return p
    log("CONNECT FAIL %s -> %s{%s}" % (from_node.get_class().get_name(),
                                       to_node.get_class().get_name(), ",".join(pins)))
    return None


def local_pos(mat):
    """逐像素局部坐标 = WorldPosition − ObjectPositionWS（物体原点常量）。
    旧版只用 ObjectPositionWS（常量）是 v5–v10 全 flat 的根因。"""
    wp = ex(mat, unreal.MaterialExpressionWorldPosition)
    op = ex(mat, unreal.MaterialExpressionObjectPositionWS)
    sub = ex(mat, unreal.MaterialExpressionSubtract)
    link(wp, sub, "A")
    link(op, sub, "B")
    return sub


# ---------------------------------------------------------------- 1. 水膜（泡沫/湿痕）
def build_film():
    mat = ensure(FILM)
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    pos = local_pos(mat)
    foam_size = scalar(mat, "FoamSize", 40.0)
    around = scalar(mat, "AroundRepeat", 1.0)
    uv = custom(mat, """
float r = length(P.xy);
float u = atan2(P.y, P.x) * 0.159154943 * max(r, 1.0) * Around;
float v = -P.z;
return float2(u, v) / max(FoamSize, 1.0);""",
                {"P": pos, "FoamSize": foam_size, "Around": around},
                unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    t = ex(mat, unreal.MaterialExpressionTime)
    speed = scalar(mat, "FoamSpeed", 0.05)
    scroll = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, scroll, "A")
    link(speed, scroll, "B")
    uv_shift = custom(mat, "return float2(0.0, T);", {"T": scroll},
                      unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    add1 = ex(mat, unreal.MaterialExpressionAdd)
    link(uv, add1, "A")
    link(uv_shift, add1, "B")
    s1 = texture_param(mat, "FoamTexture", T_FOAM_EDGE)
    link_any(add1, s1, ["UVs", "UV"])
    uv2 = ex(mat, unreal.MaterialExpressionMultiply)
    c2 = ex(mat, unreal.MaterialExpressionConstant)
    c2.set_editor_property("r", 1.63)
    link(uv, uv2, "A")
    link(c2, uv2, "B")
    speed2 = scalar(mat, "FoamSpeed2", 0.08)
    t2 = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, t2, "A")
    link(speed2, t2, "B")
    uv2_shift = custom(mat, "return float2(0.37, -T);", {"T": t2},
                       unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    add2 = ex(mat, unreal.MaterialExpressionAdd)
    link(uv2, add2, "A")
    link(uv2_shift, add2, "B")
    s2 = texture_param(mat, "FoamTexture2", T_FOAM_EDGE)
    link_any(add2, s2, ["UVs", "UV"])
    mul = ex(mat, unreal.MaterialExpressionMultiply)
    link(s1, mul, "A", "R")
    link(s2, mul, "B", "R")
    intensity = scalar(mat, "FoamIntensity", 1.0)
    mi = ex(mat, unreal.MaterialExpressionMultiply)
    link(mul, mi, "A")
    link(intensity, mi, "B")
    contrast = scalar(mat, "FoamContrast", 1.8)
    pw = ex(mat, unreal.MaterialExpressionPower)
    link(mi, pw, "Base")
    link(contrast, pw, "Exp")
    cl = ex(mat, unreal.MaterialExpressionClamp)
    link(pw, cl, "")
    foam = cl
    colour = vector(mat, "FilmColor", unreal.LinearColor(0.88, 0.93, 0.96, 1.0))
    white = ex(mat, unreal.MaterialExpressionConstant3Vector)
    white.set_editor_property("constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    lerp = ex(mat, unreal.MaterialExpressionLinearInterpolate)
    link(colour, lerp, "A")
    link(white, lerp, "B")
    link(foam, lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op_base = scalar(mat, "OpacityBase", 0.35)
    op_foam = scalar(mat, "OpacityFoam", 0.55)
    m1 = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam, m1, "A")
    link(op_foam, m1, "B")
    a1 = ex(mat, unreal.MaterialExpressionAdd)
    link(m1, a1, "A")
    link(op_base, a1, "B")
    fres = ex(mat, unreal.MaterialExpressionFresnel)
    link(scalar(mat, "FresnelPower", 4.0), fres, "ExponentIn")
    m2 = ex(mat, unreal.MaterialExpressionMultiply)
    link(fres, m2, "A")
    link(scalar(mat, "FresnelBoost", 0.25), m2, "B")
    a2 = ex(mat, unreal.MaterialExpressionAdd)
    link(a1, a2, "A")
    link(m2, a2, "B")
    oc = ex(mat, unreal.MaterialExpressionClamp)
    link(a2, oc, "")
    MEL.connect_material_property(oc, "", unreal.MaterialProperty.MP_OPACITY)
    errs = MEL.recompile_material(mat)
    check("film_compile", errs == [])
    save_fresh(mat, FILM, "M_FountainWaterFilmV2")
    return mat


# ---------------------------------------------------------------- 2. 水帘（离唇下落）
def build_cascade():
    mat = ensure(CASCADE)
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    pos = local_pos(mat)
    scale = scalar(mat, "SheetScale", 200.0)
    around = scalar(mat, "AroundRepeat", 26.0)
    uv = custom(mat, """
float r = max(length(P.xy), 0.1);
float u = atan2(P.y, P.x) * 0.159154943;
float v = -P.z / max(S, 0.001);
return float2(u * AR, v);""",
                {"P": pos, "S": scale, "AR": around},
                unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    speed = scalar(mat, "FlowSpeed", 1.4)
    t = ex(mat, unreal.MaterialExpressionTime)
    ts = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, ts, "A")
    link(speed, ts, "B")
    flow_uv = custom(mat, "return UV + float2(0.0, T);", {"UV": uv, "T": ts},
                     unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    bands = scalar(mat, "BandCount", 14.0)
    band_amp = scalar(mat, "BandStrength", 0.65)
    proc = custom(mat, """
float s = sin(UV.y * BC * 6.2831853 + sin(UV.x * 3.1 + UV.y * 2.3) * 1.4);
return saturate(0.5 + 0.5 * s * Amp);""",
                  {"UV": flow_uv, "BC": bands, "Amp": band_amp},
                  unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    foam_tex = texture_param(mat, "FoamTexture", T_FOAM_FALL)
    link_any(flow_uv, foam_tex, ["UVs", "UV"])
    foam_mul = ex(mat, unreal.MaterialExpressionMultiply)
    link(proc, foam_mul, "A")
    link(foam_tex, foam_mul, "B", "R")
    foam_amp = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam_mul, foam_amp, "A")
    link(scalar(mat, "FoamStrength", 1.8), foam_amp, "B")
    foam_cl = ex(mat, unreal.MaterialExpressionClamp)
    link(foam_amp, foam_cl, "")
    base_col = vector(mat, "SheetColor", unreal.LinearColor(0.72, 0.86, 0.90, 1.0))
    white = ex(mat, unreal.MaterialExpressionConstant3Vector)
    white.set_editor_property("constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    col = ex(mat, unreal.MaterialExpressionLinearInterpolate)
    link(base_col, col, "A")
    link(white, col, "B")
    link(foam_cl, col, "Alpha")
    emis = ex(mat, unreal.MaterialExpressionMultiply)
    link(col, emis, "A")
    link(scalar(mat, "EmissiveGain", 1.1), emis, "B")
    MEL.connect_material_property(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op_base = scalar(mat, "OpacityBase", 0.55)
    op_foam = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam_cl, op_foam, "A")
    link(scalar(mat, "OpacityFoam", 0.4), op_foam, "B")
    op_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(op_base, op_sum, "A")
    link(op_foam, op_sum, "B")
    op_cl = ex(mat, unreal.MaterialExpressionClamp)
    link(op_sum, op_cl, "")
    max_mode = getattr(unreal.ClampMode, "CMODE_CLAMP_MAX", None)
    if max_mode is not None:
        op_cl.set_editor_property("clamp_mode", max_mode)
    op_cl.set_editor_property("max_default", 0.92)
    MEL.connect_material_property(op_cl, "", unreal.MaterialProperty.MP_OPACITY)
    errs = MEL.recompile_material(mat)
    check("cascade_compile", errs == [])
    save_fresh(mat, CASCADE, "M_FountainCascadeFlowV2")
    return mat


# ---------------------------------------------------------------- 3. 盆底焦散（加法光）
def build_caustics():
    mat = ensure(CAUSTICS)
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    pos = local_pos(mat)
    t = ex(mat, unreal.MaterialExpressionTime)
    speed = scalar(mat, "Speed", 0.25)
    ts = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, ts, "A")
    link(speed, ts, "B")
    uv = custom(mat, "return P.xy / max(Tiling, 0.001) + float2(T, T * 0.6);",
                {"P": pos, "Tiling": scalar(mat, "Tiling", 90.0), "T": ts},
                unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    tex = texture_param(mat, "CausticsTexture", T_CAUSTICS)
    link_any(uv, tex, ["UVs", "UV"])
    col = vector(mat, "Colour", unreal.LinearColor(0.42, 0.68, 0.66, 1.0))
    mul = ex(mat, unreal.MaterialExpressionMultiply)
    link(tex, mul, "A", "RGB")
    link(col, mul, "B")
    emis = ex(mat, unreal.MaterialExpressionMultiply)
    link(mul, emis, "A")
    link(scalar(mat, "Intensity", 0.5), emis, "B")
    MEL.connect_material_property(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    errs = MEL.recompile_material(mat)
    check("caustics_compile", errs == [])
    save_fresh(mat, CAUSTICS, "M_FountainCausticsOverlayV2")
    return mat


# ---------------------------------------------------------------- 4. 水面（WPO 起伏 + 同源法线）
WAVE_BODY = """
float2 p = P.xy / max(FS, 0.001);
float t = T;
float h = 0.0;
float2 g = float2(0.0, 0.0);
{
    float2 d = normalize(float2(1.0, 0.30));
    float k = 6.2831853 / max(L1, 0.001);
    float ph = dot(p, d) * k - t * S1;
    h += sin(ph) * A1;
    g += cos(ph) * k * A1 * d;
}
{
    float2 d = normalize(float2(-0.55, 1.0));
    float k = 6.2831853 / max(L2, 0.001);
    float ph = dot(p, d) * k - t * S2;
    h += sin(ph) * A2;
    g += cos(ph) * k * A2 * d;
}
{
    float r = length(p);
    float R[2] = { RA, RB };
    float2 dr = r > 0.01 ? p / r : float2(0, 1);
    for (int i = 0; i < 2; ++i)
    {
        float d = r - R[i];
        float k = 6.2831853 / max(Lam, 0.001);
        float ph = d * k - t * Freq * 6.2831853;
        float env = exp(-abs(d) / max(Width, 0.001));
        h += sin(ph) * env * RAS;
        g += cos(ph) * k * env * RAS * dr;
    }
}
h += (N.r - 0.5) * 2.0 * NS;
g += float2((N.r - N2.r) / max(NoiseDelta, 0.001), (N.r - N3.r) / max(NoiseDelta, 0.001)) * NS;
"""


def build_wave():
    mat = ensure(WAVE)
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("two_sided", True)
    tlm = getattr(unreal.TranslucencyLightingMode, "TLM_SURFACE_PER_PIXEL_LIGHTING", None)
    if tlm is not None:
        mat.set_editor_property("translucency_lighting_mode", tlm)
    mat.set_editor_property("tangent_space_normal", False)
    pos = local_pos(mat)
    t = ex(mat, unreal.MaterialExpressionTime)
    noise_speed = scalar(mat, "NoiseSpeed", 0.4)
    ts = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, ts, "A")
    link(noise_speed, ts, "B")
    noise_scale = scalar(mat, "NoiseScale", 120.0)
    noise_delta = scalar(mat, "NoiseDelta", 5.0)
    uv = custom(mat, "return P.xy / max(NS, 0.001) + float2(0.0, T);",
                {"P": pos, "NS": noise_scale, "T": ts},
                unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    uv2 = custom(mat, "return UV + float2(D, 0.0) / max(S, 0.001);",
                 {"UV": uv, "D": noise_delta, "S": noise_scale},
                 unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    uv3 = custom(mat, "return UV + float2(0.0, D) / max(S, 0.001);",
                 {"UV": uv, "D": noise_delta, "S": noise_scale},
                 unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    n1 = texture_param(mat, "NoiseTex", T_NOISE)
    n2 = texture_param(mat, "NoiseTex2", T_NOISE)
    n3 = texture_param(mat, "NoiseTex3", T_NOISE)
    link_any(uv, n1, ["UVs", "UV"])
    link_any(uv2, n2, ["UVs", "UV"])
    link_any(uv3, n3, ["UVs", "UV"])
    inputs = {"P": pos, "T": t, "N": n1, "N2": n2, "N3": n3,
              "NS": scalar(mat, "NoiseStrength", 0.5),
              "NoiseDelta": noise_delta,
              "L1": scalar(mat, "Wave1Length", 160.0), "S1": scalar(mat, "Wave1Speed", 0.5),
              "A1": scalar(mat, "Wave1Amp", 0.5),
              "L2": scalar(mat, "Wave2Length", 90.0), "S2": scalar(mat, "Wave2Speed", 0.8),
              "A2": scalar(mat, "Wave2Amp", 0.35),
              "RA": scalar(mat, "RippleRadiusA", 92.0), "RB": scalar(mat, "RippleRadiusB", 137.0),
              "Lam": scalar(mat, "RippleLambda", 78.0), "Freq": scalar(mat, "RippleFreq", 0.6),
              "Width": scalar(mat, "RippleWidth", 260.0),
              "RAS": scalar(mat, "RippleStrength", 1.2),
              "FS": scalar(mat, "FountainScale", SCALE)}
    itypes = {k: (unreal.CustomMaterialOutputType.CMOT_FLOAT3
                  if k in ("P", "N", "N2", "N3") else unreal.CustomMaterialOutputType.CMOT_FLOAT1)
              for k in inputs}
    height = custom(mat, WAVE_BODY + "\nreturn h;", inputs,
                    unreal.CustomMaterialOutputType.CMOT_FLOAT1, itypes)
    wh = scalar(mat, "WaveHeight", 9.0)
    wpo_h = ex(mat, unreal.MaterialExpressionMultiply)
    link(height, wpo_h, "A")
    link(wh, wpo_h, "B")
    wpo = custom(mat, "return float3(0.0, 0.0, H);", {"H": wpo_h},
                 unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    MEL.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    nrm_inputs = dict(inputs, WH=wh, NSL=scalar(mat, "NormalSlope", 2.2))
    nrm_types = dict(itypes, WH=unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                     NSL=unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    nrm = custom(mat, WAVE_BODY + """
float slope = WH * NSL;
return normalize(float3(-g.x * slope, -g.y * slope, 1.0));""",
                 nrm_inputs, unreal.CustomMaterialOutputType.CMOT_FLOAT3, nrm_types)
    MEL.connect_material_property(nrm, "", unreal.MaterialProperty.MP_NORMAL)
    shallow = vector(mat, "WaterColorShallow", unreal.LinearColor(0.30, 0.62, 0.64, 1.0))
    deep = vector(mat, "WaterColorDeep", unreal.LinearColor(0.05, 0.20, 0.25, 1.0))
    sd = ex(mat, unreal.MaterialExpressionSceneTexture)
    enum = getattr(unreal.SceneTextureId, "PPI_SCENE_DEPTH", None)
    if enum is not None:
        sd.set_editor_property("scene_texture_id", enum)
    pixel = ex(mat, unreal.MaterialExpressionPixelDepth)
    sub = ex(mat, unreal.MaterialExpressionSubtract)
    link(sd, sub, "A", "Color")
    link(pixel, sub, "B")
    div = ex(mat, unreal.MaterialExpressionDivide)
    link(sub, div, "A")
    link(scalar(mat, "DepthScale", 190.0), div, "B")
    fade = ex(mat, unreal.MaterialExpressionClamp)
    link(div, fade, "")
    col = ex(mat, unreal.MaterialExpressionLinearInterpolate)
    link(shallow, col, "A")
    link(deep, col, "B")
    link(fade, col, "Alpha")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    fres = ex(mat, unreal.MaterialExpressionFresnel)
    link(scalar(mat, "FresnelPower", 3.0), fres, "ExponentIn")
    sky = cube_param(mat, "ReflectionCubemap", CUBEMAP)
    refl_cls = getattr(unreal, "MaterialExpressionReflectionVectorWS", None)
    if refl_cls:
        link_any(ex(mat, refl_cls), sky, ["UV", "UVs"])
    sky_mul = ex(mat, unreal.MaterialExpressionMultiply)
    link(sky, sky_mul, "A", "RGB")
    link(scalar(mat, "ReflectionStrength", 1.0), sky_mul, "B")
    emis = ex(mat, unreal.MaterialExpressionMultiply)
    link(sky_mul, emis, "A")
    link(fres, emis, "B")
    crest = ex(mat, unreal.MaterialExpressionClamp)
    link(height, crest, "")
    crest_boost = ex(mat, unreal.MaterialExpressionMultiply)
    link(crest, crest_boost, "A")
    link(scalar(mat, "CrestFoam", 0.6), crest_boost, "B")
    emis_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(emis, emis_sum, "A")
    link(crest_boost, emis_sum, "B")
    MEL.connect_material_property(emis_sum, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op_base = ex(mat, unreal.MaterialExpressionMultiply)
    link(scalar(mat, "OpacityBase", 0.5), op_base, "A")
    link(fade, op_base, "B")
    op_fres = ex(mat, unreal.MaterialExpressionMultiply)
    link(fres, op_fres, "A")
    link(scalar(mat, "FresnelOpacity", 0.35), op_fres, "B")
    op_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(op_base, op_sum, "A")
    link(op_fres, op_sum, "B")
    op_cl = ex(mat, unreal.MaterialExpressionClamp)
    link(op_sum, op_cl, "")
    max_mode = getattr(unreal.ClampMode, "CMODE_CLAMP_MAX", None)
    if max_mode is not None:
        op_cl.set_editor_property("clamp_mode", max_mode)
    op_cl.set_editor_property("max_default", 0.75)
    MEL.connect_material_property(op_cl, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(scalar(mat, "Roughness", 0.05), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(scalar(mat, "Specular", 1.0), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.connect_material_property(scalar(mat, "Metallic", 0.0), "", unreal.MaterialProperty.MP_METALLIC)
    errs = MEL.recompile_material(mat)
    check("wave_compile", errs == [])
    log("wave expressions: %d" % len(MEL.get_material_expressions(mat) or []))
    save_fresh(mat, WAVE, "M_FountainWaveWaterV2")
    return mat


# ---------------------------------------------------------------- 5. MIC 换父级 + 重调
def reparent(mic_path, new_parent):
    mic = unreal.load_asset(mic_path)
    if not mic:
        check("mic_%s" % mic_path.rsplit("/", 1)[1], False)
        return
    mic.set_editor_property("parent", new_parent)
    ok = mic.get_editor_property("parent") == new_parent
    check("mic_parent_%s" % mic_path.rsplit("/", 1)[1], ok)
    log("mic %s parent -> %s" % (mic_path.rsplit("/", 1)[1], new_parent.get_name()))


def set_scalars(mic_path, values):
    mic = unreal.load_asset(mic_path)
    if not mic:
        return
    for name, val in values.items():
        MEL.set_material_instance_scalar_parameter_value(mic, name, val)
    names = []
    for v in (mic.get_editor_property("scalar_parameter_values") or []):
        try:
            names.append(v.parameter_info.name)
        except Exception:
            pass
    log("mic %s overrides=%d %s" % (mic_path.rsplit("/", 1)[1], len(names), sorted(set(values)) and ""))


# ---------------------------------------------------------------- 6. FX 网格原地重建
PIECES = [
    # 水线泡沫环（水平环，略高于水面，收在碗内壁内）
    ("foam_wall0", 0, 96, [(182.0, 74.3), (198.0, 74.3), (198.0, 75.1), (182.0, 75.1)]),
    ("foam_wall1", 0, 64, [(110.5, 206.3), (129.0, 206.3), (129.0, 207.1), (110.5, 207.1)]),
    ("foam_wall2", 0, 64, [(73.0, 282.3), (85.0, 282.3), (85.0, 283.1), (73.0, 283.1)]),
    # 穿出物接触环
    ("foam_socle", 0, 64, [(91.5, 74.3), (100.0, 74.3), (100.0, 75.3), (91.5, 75.3)]),
    ("foam_ped2", 0, 48, [(40.5, 206.3), (50.0, 206.3), (50.0, 207.3), (40.5, 207.3)]),
    ("foam_pigna", 0, 48, [(31.5, 282.3), (40.0, 282.3), (40.0, 283.3), (31.5, 283.3)]),
    # 湿痕带（碗内壁水线以上，0.8cm 内贴）
    ("wet_wall0", 1, 96, [(198.0, 74.0), (196.0, 82.0), (195.2, 82.0), (197.2, 74.0)]),
    ("wet_wall1", 1, 64, [(129.0, 206.0), (131.0, 212.0), (124.0, 214.0),
                          (123.2, 213.5), (130.2, 211.5), (128.2, 206.0)]),
    ("wet_wall2", 1, 64, [(85.0, 282.0), (87.0, 286.0), (80.0, 286.0),
                          (80.0, 285.2), (86.2, 285.2), (84.2, 282.0)]),
    # 溢流水帘：离唇抛物线，挂在碗**外鼓包之外**（旧版埋进石头里只露穿墙暗矩形）
    ("fall_top_to_mid", 2, 96, [(91.0, 282.0), (94.0, 272.0), (94.5, 208.0),
                                (95.7, 208.0), (95.2, 272.0), (92.2, 283.0)]),
    ("fall_mid_to_low", 2, 96, [(134.0, 210.0), (137.0, 200.0), (137.5, 76.0),
                                (138.7, 76.0), (138.2, 200.0), (135.2, 211.0)]),
    ("fall_low_to_step", 2, 96, [(206.0, 80.0), (209.0, 70.0), (209.5, 22.0),
                                 (210.7, 22.0), (210.2, 70.0), (207.2, 81.0)]),
    ("fall_step1_to_step0", 2, 64, [(220.5, 19.0), (222.0, 12.0), (222.0, 10.5),
                                    (223.2, 10.5), (223.2, 12.5), (221.7, 19.5)]),
    # 落点泡沫环
    ("splash_mid", 0, 64, [(92.0, 206.3), (104.0, 206.3), (104.0, 207.6), (92.0, 207.6)]),
    ("splash_low", 0, 96, [(136.0, 74.3), (150.0, 74.3), (150.0, 75.6), (136.0, 75.6)]),
    ("splash_step1", 0, 96, [(206.0, 20.3), (219.6, 20.3), (219.6, 21.6), (206.0, 21.6)]),
    ("splash_step0", 0, 64, [(219.0, 10.3), (239.5, 10.3), (239.5, 11.6), (219.0, 11.6)]),
    # 盆底焦散（加法光衬底）
    ("liner_low", 3, 64, [(0.0, 44.2), (178.0, 44.6), (178.0, 45.2), (0.0, 45.2)]),
    ("liner_mid", 3, 48, [(0.0, 184.3), (108.0, 184.7), (108.0, 185.3), (0.0, 185.3)]),
    ("liner_top", 3, 48, [(0.0, 266.3), (70.0, 266.7), (70.0, 267.3), (0.0, 267.3)]),
]


def build_fx_mesh(mats):
    tf = unreal.Transform()
    tf.translation = unreal.Vector(0, 0, 0)
    tf.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    tf.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    handle = SV.create_mesh().handle
    for name, slot, steps, prof in PIECES:
        pts = [unreal.Vector2D(r * SCALE, z * SCALE) for (r, z) in prof]
        res = SV.append_revolve_polygon(handle, tf, pts, 0.0, steps, 360.0, slot)
        log("piece %-20s slot=%d %s" % (name, slot, getattr(res, "success", None)))
    info = SV.get_mesh_info(handle)
    log("fx mesh: tris=%d comps=%d open=%d" % (
        info.triangle_count, info.connected_components, info.open_border_edges))
    check("fx_closed", info.open_border_edges == 0)
    SV.save_mesh_to_static_mesh(handle, FX_MESH, True, True, False, True)
    SV.release_mesh(handle)
    time.sleep(1.0)
    m = unreal.load_asset(FX_MESH)
    slots = list(m.get_editor_property("static_materials") or [])
    while len(slots) < 4:
        slots.append(unreal.StaticMaterial())
    for i, mat in enumerate(mats):
        slots[i].set_editor_property("material_interface", mat)
    m.set_editor_property("static_materials", slots)
    m.modify()
    EAL.save_loaded_asset(m, True)
    stamp = save_fresh(m, FX_MESH, "SM_RomanFountain_WaterFX")
    m = unreal.load_asset(FX_MESH)
    names = [m.get_material(i).get_name() if m.get_material(i) else "None" for i in range(4)]
    log("fx slots: %s" % names)
    check("fx_slots", names == [x.get_name() for x in mats])
    return stamp


# ---------------------------------------------------------------- run
film = build_film()
cascade = build_cascade()
caustics = build_caustics()
wave = build_wave()

reparent(MATDIR + "/MIC_FountainFoam", film)
reparent(MATDIR + "/MIC_FountainWet", film)
reparent(MATDIR + "/MIC_FountainCascadeFlow", cascade)
reparent(MATDIR + "/MIC_FountainCaustics", caustics)
reparent(MATDIR + "/MIC_FountainWaveWater", wave)

mic_foam = unreal.load_asset(MATDIR + "/MIC_FountainFoam")
mic_wet = unreal.load_asset(MATDIR + "/MIC_FountainWet")
mic_cas = unreal.load_asset(MATDIR + "/MIC_FountainCascadeFlow")
mic_cau = unreal.load_asset(MATDIR + "/MIC_FountainCaustics")
mic_wav = unreal.load_asset(MATDIR + "/MIC_FountainWaveWater")
if mic_wav:
    set_scalars(MATDIR + "/MIC_FountainWaveWater", {
        "WaveHeight": 9.0, "NormalSlope": 2.2,
        "Wave1Length": 160.0, "Wave1Amp": 0.5, "Wave1Speed": 0.5,
        "Wave2Length": 90.0, "Wave2Amp": 0.35, "Wave2Speed": 0.8,
        "NoiseScale": 120.0, "NoiseStrength": 0.5, "NoiseSpeed": 0.4,
        "RippleStrength": 1.2, "CrestFoam": 0.6,
        "OpacityBase": 0.5, "FresnelOpacity": 0.35, "ReflectionStrength": 1.0})
if mic_cas:
    set_scalars(MATDIR + "/MIC_FountainCascadeFlow", {
        "FlowSpeed": 1.4, "BandCount": 14.0, "BandStrength": 0.65,
        "OpacityBase": 0.55, "FoamStrength": 1.8, "EmissiveGain": 1.1})
if mic_foam:
    set_scalars(MATDIR + "/MIC_FountainFoam", {"FoamSize": 40.0, "OpacityBase": 0.35,
                                               "OpacityFoam": 0.55, "FoamSpeed": 0.05})
if mic_wet:
    set_scalars(MATDIR + "/MIC_FountainWet", {"OpacityBase": 0.3})
if mic_cau:
    set_scalars(MATDIR + "/MIC_FountainCaustics", {"Intensity": 0.5})
for mic in (mic_foam, mic_wet, mic_cas, mic_cau, mic_wav):
    if mic:
        EAL.save_loaded_asset(mic, True)

if SV is not None:
    build_fx_mesh([mic_foam, mic_wet, mic_cas, mic_cau])
else:
    check("modeling_service", False)

fails = [k for k, v in LOG if not v]
log("checks=%d failed=%d %s" % (len(LOG), len(fails), fails))
log("RESULT: %s" % ("PASS" if not fails else "FAIL"))
