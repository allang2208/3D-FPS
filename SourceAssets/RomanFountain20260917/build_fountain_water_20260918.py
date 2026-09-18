"""Fountain water pass (2026-09-18, user-approved: "更像水 + 做溢流和落水，从上往下流淌").

What this builds (all assets, no level edits):

1. `M_FountainWaterFilm` — 工程自制的水膜/泡沫/溢流材质（Unlit + Translucent + TwoSided）。
   自算**柱面 UV**（从物体空间位置取 atan2 与 z，按世界尺寸 FoamSize 归一），所以泡沫/水痕不依赖
   网格 UV（本工程网格走 XAtlas，UV 方向不可控）；两层泡沫贴图反向滚动 + 对比度 + Fresnel 提亮。
   水帘的动感靠**两层泡沫贴图快速反向滚动**表现（原计划的 WPO 径向摆动在无头 MaterialEditor 里
   触发 `!IsRooted()` 断言，已去掉；要摆动得在编辑器里手工加 WPO 或改用 Niagara ribbon）。
   实例（都在 `Props/RomanFountain20260917/Materials` 下，暴露参数，用户可在编辑器里直接调）：
     MIC_FountainFoam    白泡沫（水线/落点/穿出物周围的接触环）
     MIC_FountainWet     深色湿膜（水线以上到盘沿的湿痕带）
     MIC_FountainCascade 溢流水帘（快速向下滚动的条状泡沫）
2. `M_FountainWater` + `MIC_FountainWater` — **工程自制水面材质**（Default Lit + Translucent + TwoSided）：
   极坐标 UV 的两层滚动法线、**落水驱动的解析涟漪**（在两个落点半径上生成向外的涟漪波列）、
   依据场景深度的"浅→深"配色与透明度、菲涅尔天空反射（立方图）、波峰泡沫。
   （v5 用包内 `M_Water_Clean` 实例被用户判为"深色固体"，这轮改成自建材质并把亮度/动感调到水。）
3. `MIC_FountainCaustics` — 包内 `M_Caustics` 实例（盆底衬底）。
4. `SM_RomanFountain_WaterFX` — 新网格：水线接触环、湿痕带、穿出物（基座/柱墩/松果）接触环、
   三级溢流水帘（顶盘→中盘→大盘→台阶）、落点泡沫环、盆底焦散衬底。薄壁实体（闭合剖面，0 开放边）。
5. 把主网格 `SM_RomanFountain_20` 的 slot1（水）换成 `MIC_FountainWater`；大理石 slot0 不动
   （面板构件落地时 `AVoxelBuildPrefabActor::Configure` 只覆盖 slot0，水/泡沫槽保持）。

碰撞：WaterFX 网格**不生成碰撞**（运行时由 Actor 把该组件设为 NoCollision）；主网格碰撞不改。

尺寸表按 1× 模型写（与 `build_fountain_20260917.py` 的 PROFILES 同源），构建时统一乘 SCALE=2。
水位（1×）：大盘 74、中盘 206、顶盘 282；盘沿：82 / 214 / 286；基座鼓座在水线处 r≈92.7。

运行（编辑器关闭时最稳；有别的 UnrealEditor/Cmd 在跑会让保存静默失败）：
  UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
      -Script=D:/FPS3D/FPSGAME/SourceAssets/RomanFountain20260917/build_fountain_water_20260918.py \
      -unattended -nop4 -nosplash -NullRHI -nosound -abslog=<日志>
"""

import os
import time

import unreal

SV = unreal.ModelingService
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

DIR = "/Game/Props/RomanFountain20260917"
MATDIR = DIR + "/Materials"
FULL = DIR + "/SM_RomanFountain_20"
FX = DIR + "/SM_RomanFountain_WaterFX"
MARBLE = "/Game/Props/RomanColumn20260915/M_RomanStone_V2"
FILM = MATDIR + "/M_FountainWaterFilm"
WATER_MAT = MATDIR + "/M_FountainWater"
CASCADE_MAT = MATDIR + "/M_FountainCascadeFlow"
CASCADE_INST = MATDIR + "/MIC_FountainCascadeFlow"
HIDDEN_MAT = MATDIR + "/M_FountainHidden"
WAVE_MAT = MATDIR + "/M_FountainWaveWater"
WAVE_INST = MATDIR + "/MIC_FountainWaveWater"
WAVE_MESH = DIR + "/SM_RomanFountain_WaterWaves"
PACK = "/Game/WaterMaterials"
CLEAN = PACK + "/Materials/M_Water_Clean"
CAUSTICS = PACK + "/Materials/M_Caustics"
T_FOAM_POND = PACK + "/Textures/T_Pond_Foam"
T_FOAM_EDGE = PACK + "/Textures/T_Ocean_EdgeFoam"
T_FOAM_FALL = PACK + "/Textures/T_Waterfall_Foam_Directional"
WAVE_NORMAL_A = PACK + "/Textures/T_Lake_Waves01_Normals"
WAVE_NORMAL_B = PACK + "/Textures/T_Water_Normal"
CUBEMAP = PACK + "/Textures/T_Cubemap"
NOISE_CANDIDATES = (PACK + "/Textures/T_Noises", PACK + "/Textures/T_Noise_Progressive",
                    PACK + "/Textures/T_Noise_Curves", T_FOAM_POND)
T_NOISE = next((p for p in NOISE_CANDIDATES if unreal.load_asset(p) or unreal.load_asset(p.split(".")[0])), NOISE_CANDIDATES[0])
POS_CLS = getattr(unreal, "MaterialExpressionObjectPositionWS", None) or \
    getattr(unreal, "MaterialExpressionObjectPosition", None)
SCALE = 2.0
STEPS = 96
STARTED = time.time()
LOG = []

# 1× 尺寸表（半径, 高度）；薄壁实体 = 闭合剖面绕 Z 旋转。
# 材质槽序号：0 泡沫、1 湿膜、2 溢流、3 焦散。
WATER_LOW, WATER_MID, WATER_TOP = 74.0, 206.0, 282.0
PED_SOCLE_R, PED2_R, PIGNA_R = 92.7, 42.7, 31.0

PIECES = [
    # --- 大盘（basin0）水线接触：水面泡沫环 + 内侧壁湿痕带
    ("foam_wall0", 0, 96, [(166.0, 74.2), (181.8, 74.2), (181.8, 75.0), (166.0, 75.0)]),
    ("wet_wall0", 1, 96, [(180.4, 74.0), (194.4, 82.0), (195.6, 82.0), (181.6, 74.0)]),
    # --- 中盘
    ("foam_wall1", 0, 64, [(97.0, 206.2), (110.3, 206.2), (110.3, 207.0), (97.0, 207.0)]),
    ("wet_wall1", 1, 64, [(109.5, 206.0), (123.5, 214.0), (124.7, 214.0), (110.7, 206.0)]),
    # --- 顶盘
    ("foam_wall2", 0, 64, [(60.0, 282.2), (72.8, 282.2), (72.8, 283.0), (60.0, 283.0)]),
    ("wet_wall2", 1, 64, [(72.0, 282.0), (79.5, 286.0), (80.7, 286.0), (73.2, 282.0)]),
    # --- 穿出水的实体周围接触环（基座鼓座 / ped2 / 松果）
    ("foam_socle", 0, 64, [(93.6, 74.2), (107.0, 74.2), (107.0, 75.2), (93.6, 75.2)]),
    ("foam_ped2", 0, 48, [(43.5, 206.2), (57.0, 206.2), (57.0, 207.2), (43.5, 207.2)]),
    ("foam_pigna", 0, 48, [(32.6, 282.2), (46.0, 282.2), (46.0, 283.2), (32.6, 283.2)]),
    # --- 三级溢流水帘（从上往下）：顶盘→中盘→大盘→台阶
    ("fall_top_to_mid", 2, 96, [(79.0, 286.5), (89.0, 277.5), (92.5, 277.0), (92.5, 207.5),
                                (93.7, 207.5), (93.7, 276.0), (91.5, 276.0), (80.6, 285.5)]),
    ("fall_mid_to_low", 2, 96, [(123.0, 214.5), (133.0, 203.0), (136.5, 202.0), (136.5, 75.5),
                                (137.7, 75.5), (137.7, 201.0), (135.0, 201.0), (124.1, 213.5)]),
    ("fall_low_to_step", 2, 96, [(195.0, 82.5), (203.0, 78.0), (206.0, 70.0), (206.0, 21.5),
                                 (207.2, 21.5), (207.2, 69.0), (204.5, 69.0), (196.1, 81.5)]),
    ("fall_step1_to_step0", 2, 64, [(219.0, 20.5), (219.0, 11.0), (220.2, 11.0), (220.2, 20.5)]),
    # --- 落点泡沫环（水帘砸在水面上的位置）
    ("splash_mid", 0, 64, [(92.0, 206.3), (104.0, 206.3), (104.0, 207.6), (92.0, 207.6)]),
    ("splash_low", 0, 96, [(136.0, 74.3), (150.0, 74.3), (150.0, 75.6), (136.0, 75.6)]),
    ("splash_step1", 0, 96, [(206.0, 20.3), (219.6, 20.3), (219.6, 21.6), (206.0, 21.6)]),
    ("splash_step0", 0, 64, [(219.0, 10.3), (239.5, 10.3), (239.5, 11.6), (219.0, 11.6)]),
    # --- 盆底焦散衬底（略高于盆底，透过半透明水可见）
    ("liner_low", 3, 64, [(0.0, 44.2), (178.0, 44.6), (178.0, 45.2), (0.0, 45.2)]),
    ("liner_mid", 3, 48, [(0.0, 184.3), (108.0, 184.7), (108.0, 185.3), (0.0, 185.3)]),
    ("liner_top", 3, 48, [(0.0, 266.3), (70.0, 266.7), (70.0, 267.3), (0.0, 267.3)]),
]


def log(m):
    print("[water] " + m)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-30s %s" % (label, "OK" if ok else "FAIL"))
    return ok


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


def save_fresh(asset, path, label):
    EAL.save_loaded_asset(asset, True)
    unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(path)], False)
    stamp = None
    for _ in range(10):
        stamp = disk(path)
        if stamp and stamp[2] >= STARTED - 120.0:
            break
        time.sleep(1.0)
        EAL.save_loaded_asset(asset, True)
    log("saved %-28s %s" % (label, stamp))
    return stamp


def ensure_asset(path, cls, factory):
    a = EAL.load_asset(path) or unreal.load_asset(path)
    if a:
        return a
    folder, name = path.rsplit("/", 1)
    EAL.make_directory(folder)
    # create_asset 要的是工厂**实例**；允许传类，由这里实例化
    fac = factory() if isinstance(factory, type) else factory
    return TOOLS.create_asset(name, folder, cls, fac)


def param_node(mat, cls, name):
    n = MEL.create_material_expression(mat, cls)
    n.set_editor_property("parameter_name", name)
    return n


def scalar(mat, name, value):
    n = param_node(mat, unreal.MaterialExpressionScalarParameter, name)
    n.set_editor_property("default_value", value)
    return n


def vector(mat, name, value):
    n = param_node(mat, unreal.MaterialExpressionVectorParameter, name)
    n.set_editor_property("default_value", value)
    return n


def texture_param(mat, name, tex_path):
    n = param_node(mat, unreal.MaterialExpressionTextureSampleParameter2D, name)
    tex = unreal.load_asset(tex_path)
    if tex:
        n.set_editor_property("texture", tex)
    return n


def cube_param(mat, name, tex_path):
    n = param_node(mat, unreal.MaterialExpressionTextureSampleParameterCube, name)
    tex = unreal.load_asset(tex_path)
    if tex:
        n.set_editor_property("texture", tex)
    return n


def custom(mat, code, inputs, output_type=None, input_types=None):
    n = MEL.create_material_expression(mat, unreal.MaterialExpressionCustom)
    if output_type is not None:
        n.set_editor_property("output_type", output_type)
    n.set_editor_property("code", code)
    pins = []
    for pin_name in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", pin_name)
        pins.append(pin)
    n.set_editor_property("inputs", pins)
    for pin_name, source in inputs.items():
        MEL.connect_material_expressions(source, "", n, pin_name)
    return n


def ex(mat, cls):
    return MEL.create_material_expression(mat, cls)


def link(from_node, to_node, to_pin, from_pin=""):
    ok = MEL.connect_material_expressions(from_node, from_pin, to_node, to_pin)
    if not ok:
        log("connect %s -> %s.%s failed" % (from_node.get_class().get_name(), to_node.get_class().get_name(), to_pin))
    return ok


def link_any(from_node, to_node, pins, from_pin=""):
    """引脚名在不同版本里可能不同：按候选依次尝试，成功即返回。"""
    for p in pins:
        if MEL.connect_material_expressions(from_node, from_pin, to_node, p):
            return p
    log("connect %s -> %s{%s} all failed" % (
        from_node.get_class().get_name(), to_node.get_class().get_name(), ",".join(pins)))
    return None


def scene_depth_node(mat, want_depth=True):
    n = ex(mat, unreal.MaterialExpressionSceneTexture)
    enum = None
    # 真实枚举名（探针 probe_water_state_20260918.py 读出）：PPI_SCENE_DEPTH / PPI_SCENE_COLOR
    for cand in ("PPI_SCENE_DEPTH" if want_depth else "PPI_SCENE_COLOR",):
        enum = getattr(unreal.SceneTextureId, cand, None)
    if enum is not None:
        n.set_editor_property("scene_texture_id", enum)
    else:
        log("WARN: SceneTextureId 里没有 %s —— 节点会退回默认 SceneColor，深度会失真" % cand)
    return n


# ------------------------------------------------------------------ 1. 水膜材质
def build_film_material():
    mat = ensure_asset(FILM, unreal.Material, unreal.MaterialFactoryNew)
    if not mat:
        check("film_material_created", False)
        return None
    check("film_material_created", True)
    if (MEL.get_material_expressions(mat) or []):
        # 已是成品：**不要**重建表达式表。该材质已被 FX 网格的槽经实例引用，
        # 无头 MaterialEditor 里 delete_all_material_expressions 会断言 !IsRooted() 直接崩进程。
        # 要改图：先断开引用（删掉实例/网格槽）或换一个新资产名重建。
        log("film material exists (%d expressions) - skip rebuild, only instances are retuned"
            % len(MEL.get_material_expressions(mat) or []))
        return mat
    log("step: delete_all_material_expressions")
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)

    # 柱面 UV：物体空间 atan2/2π × 半径、-z，按世界尺寸 FoamSize(cm) 归一 —— 与网格 UV 无关。
    pos_cls = None
    for cand in ("MaterialExpressionObjectPositionWS", "MaterialExpressionObjectPosition"):
        if hasattr(unreal, cand):
            pos_cls = getattr(unreal, cand)
            break
    if pos_cls is None:
        check("object_position_node", False)
        return None
    log("object position node: %s" % pos_cls.__name__)
    pos = ex(mat, pos_cls)
    log("step: pos node ok")
    foam_size = scalar(mat, "FoamSize", 60.0)
    around = scalar(mat, "AroundRepeat", 1.0)
    log("step: scalars ok")
    uv = custom(mat, """
float r = length(P.xy);
float u = atan2(P.y, P.x) * 0.159154943 * max(r, 1.0) * Around;
float v = -P.z;
return float2(u, v) / max(FoamSize, 1.0);""",
                {"P": pos, "FoamSize": foam_size, "Around": around},
                unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                {"P": unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                 "FoamSize": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                 "Around": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    log("step: uv custom ok")

    speed = scalar(mat, "FoamSpeed", 0.03)
    t = ex(mat, unreal.MaterialExpressionTime)
    scroll = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, scroll, "A")
    link(speed, scroll, "B")
    uv_shift = custom(mat, "return float2(0.0, T);", {"T": scroll},
                      unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                      {"T": unreal.CustomMaterialOutputType.CMOT_FLOAT1})

    add1 = ex(mat, unreal.MaterialExpressionAdd)
    link(uv, add1, "A")
    link(uv_shift, add1, "B")
    s1 = texture_param(mat, "FoamTexture", T_FOAM_EDGE)
    link(add1, s1, "UVs")
    log("step: sample1 ok")

    # 第二层：缩放 + 反向/更快，制造两向流动
    uv2 = ex(mat, unreal.MaterialExpressionMultiply)
    c2 = ex(mat, unreal.MaterialExpressionConstant)
    c2.set_editor_property("r", 1.63)
    link(uv, uv2, "A")
    link(c2, uv2, "B")
    speed2 = scalar(mat, "FoamSpeed2", 0.055)
    t2 = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, t2, "A")
    link(speed2, t2, "B")
    uv2_shift = custom(mat, "return float2(0.37, -T);", {"T": t2},
                       unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                       {"T": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    add2 = ex(mat, unreal.MaterialExpressionAdd)
    link(uv2, add2, "A")
    link(uv2_shift, add2, "B")
    s2 = texture_param(mat, "FoamTexture2", T_FOAM_EDGE)
    link(add2, s2, "UVs")
    log("step: sample2 ok")

    mul = ex(mat, unreal.MaterialExpressionMultiply)
    link(s1, mul, "A", "R")
    link(s2, mul, "B", "R")
    intensity = scalar(mat, "FoamIntensity", 1.0)
    mi = ex(mat, unreal.MaterialExpressionMultiply)
    link(mul, mi, "A")
    link(intensity, mi, "B")
    contrast = scalar(mat, "FoamContrast", 1.6)
    pw = ex(mat, unreal.MaterialExpressionPower)
    link(mi, pw, "Base")
    link(contrast, pw, "Exp")
    cl = ex(mat, unreal.MaterialExpressionClamp)
    link(pw, cl, "")
    foam = cl
    log("step: foam chain ok")

    colour = vector(mat, "FilmColor", unreal.LinearColor(0.88, 0.93, 0.96, 1.0))
    white = ex(mat, unreal.MaterialExpressionConstant3Vector)
    white.set_editor_property("constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    lerp = ex(mat, unreal.MaterialExpressionLinearInterpolate)
    link(colour, lerp, "A")
    link(white, lerp, "B")
    link(foam, lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    op_base = scalar(mat, "OpacityBase", 0.45)
    op_foam = scalar(mat, "OpacityFoam", 0.45)
    m1 = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam, m1, "A")
    link(op_foam, m1, "B")
    a1 = ex(mat, unreal.MaterialExpressionAdd)
    link(m1, a1, "A")
    link(op_base, a1, "B")
    # Fresnel：掠射角更实，薄片才有水膜感
    fres = ex(mat, unreal.MaterialExpressionFresnel)
    fp = scalar(mat, "FresnelPower", 4.0)
    link(fp, fres, "ExponentIn")
    fb = scalar(mat, "FresnelBoost", 0.25)
    m2 = ex(mat, unreal.MaterialExpressionMultiply)
    link(fres, m2, "A")
    link(fb, m2, "B")
    a2 = ex(mat, unreal.MaterialExpressionAdd)
    link(a1, a2, "A")
    link(m2, a2, "B")
    oc = ex(mat, unreal.MaterialExpressionClamp)
    link(a2, oc, "")
    MEL.connect_material_property(oc, "", unreal.MaterialProperty.MP_OPACITY)

    # 所以这里记录返回值、并用"输出属性挂到哪个表达式 + 表达式数量"当结构证据。
    log("recompile_material -> %s" % ok)
    exprs = MEL.get_material_expressions(mat) or []
    log("film expressions: %d" % len(exprs))
    for prop, label in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, "Emissive"),
                        (unreal.MaterialProperty.MP_OPACITY, "Opacity")):
        try:
            node = MEL.get_material_property_input_node(mat, prop)
            log("%s <- %s" % (label, node.get_class().get_name() if node else "None"))
        except Exception as exc:  # noqa: BLE001
            log("%s readback failed: %s" % (label, exc))
    check("film_expressions", len(exprs) >= 20)
    save_fresh(mat, FILM, "M_FountainWaterFilm")
    return mat


# ------------------------------------------------------------------ 2. 实例
WAVE_BODY = """
float2 p = P.xy / max(FS, 0.001);            // 1× 单位
float t = T;
float h = 0.0;
float2 g = float2(0.0, 0.0);                 // 解析梯度 dh/dp
// 两层方向不同的正弦（波长 L、速度 S、振幅 A）
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
// 落水涟漪（两个落点半径向外的波列，按距离衰减）
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
// 噪声（两张采样做方向导数）→ 不规则起伏，避免"规整正弦"的机械感
h += (N.r - 0.5) * 2.0 * NS;
g += float2((N.r - N2.r) / max(NoiseDelta, 0.001), (N.r - N3.r) / max(NoiseDelta, 0.001)) * NS;
"""


def wave_node_inputs(mat, pos):
    """WAVE_BODY 需要的标量/采样输入（两张噪声采样图共用 FoamTexture 之外的 NoiseTex）。"""
    noise_uv_scale = scalar(mat, "NoiseScale", 260.0)
    noise_speed = scalar(mat, "NoiseSpeed", 0.35)
    noise_offset = scalar(mat, "NoiseDelta", 6.0)
    t = ex(mat, unreal.MaterialExpressionTime)
    ts = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, ts, "A")
    link(noise_speed, ts, "B")
    uv = custom(mat, "return P.xy / max(NS, 0.001) + float2(0.0, T);",
                {"P": pos, "NS": noise_uv_scale, "T": ts},
                unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                {"P": unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                 "NS": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                 "T": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    uv2 = custom(mat, "return UV + float2(D, 0.0) / max(S, 0.001);",
                 {"UV": uv, "D": noise_offset, "S": noise_uv_scale},
                 unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                 {"UV": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                  "D": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                  "S": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    uv3 = custom(mat, "return UV + float2(0.0, D) / max(S, 0.001);",
                 {"UV": uv, "D": noise_offset, "S": noise_uv_scale},
                 unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                 {"UV": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                  "D": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                  "S": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    n1 = texture_param(mat, "NoiseTex", T_NOISE)
    n2 = texture_param(mat, "NoiseTex2", T_NOISE)
    n3 = texture_param(mat, "NoiseTex3", T_NOISE)
    link_any(uv, n1, ["UVs", "UV"])
    link_any(uv2, n2, ["UVs", "UV"])
    link_any(uv3, n3, ["UVs", "UV"])
    return {"P": pos, "T": t,
            "N": n1, "N2": n2, "N3": n3,
            "NS": scalar(mat, "NoiseStrength", 0.35),
            "NoiseDelta": noise_offset,
            "L1": scalar(mat, "Wave1Length", 300.0), "S1": scalar(mat, "Wave1Speed", 0.55),
            "A1": scalar(mat, "Wave1Amp", 0.55),
            "L2": scalar(mat, "Wave2Length", 170.0), "S2": scalar(mat, "Wave2Speed", 0.85),
            "A2": scalar(mat, "Wave2Amp", 0.35),
            "RA": scalar(mat, "RippleRadiusA", 92.0), "RB": scalar(mat, "RippleRadiusB", 137.0),
            "Lam": scalar(mat, "RippleLambda", 78.0), "Freq": scalar(mat, "RippleFreq", 0.6),
            "Width": scalar(mat, "RippleWidth", 260.0), "RAS": scalar(mat, "RippleStrength", 1.1),
            "FS": scalar(mat, "FountainScale", SCALE)}


def build_wave_water_material():
    """会**真正起伏**的水面材质：几何 WPO（多层正弦 + 噪声）+ 与之同源的解析世界空间法线。

    上一版只做了"平面上的法线扰动"，几何完全不动 → 轮廓恒定，读起来还是固体。
    水面都是水平盘面，所以法线用世界空间（`tangent_space_normal = False`），
    与 WPO 的高度场解析梯度一致，避免"看起来在动但亮面不动"。
    """
    mat = ensure_asset(WAVE_MAT, unreal.Material, unreal.MaterialFactoryNew)
    if not mat or (MEL.get_material_expressions(mat) or []):
        log("wave water material exists - skip rebuild")
        return mat
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("two_sided", True)
    tlm = getattr(unreal.TranslucencyLightingMode, "TLM_SURFACE_PER_PIXEL_LIGHTING", None)
    if tlm is not None:
        mat.set_editor_property("translucency_lighting_mode", tlm)
    mat.set_editor_property("tangent_space_normal", False)

    pos = ex(mat, POS_CLS)
    inputs = wave_node_inputs(mat, pos)

    # ① 几何：高度场 × WaveHeight 作为 WPO
    height = custom(mat, WAVE_BODY + "\nreturn h;", inputs,
                    unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                    {k: (unreal.CustomMaterialOutputType.CMOT_FLOAT3
                         if k in ("P", "N", "N2", "N3") else unreal.CustomMaterialOutputType.CMOT_FLOAT1)
                     for k in inputs})
    wh = scalar(mat, "WaveHeight", 7.0)
    wpo_h = ex(mat, unreal.MaterialExpressionMultiply)
    link(height, wpo_h, "A")
    link(wh, wpo_h, "B")
    wpo = custom(mat, "return float3(0.0, 0.0, H);", {"H": wpo_h},
                 unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                 {"H": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    MEL.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    # ② 法线：高度场梯度的负值（世界空间，向上 +Z），与几何同源
    nrm = custom(mat, WAVE_BODY + """
float slope = WH * NSL;
return normalize(float3(-g.x * slope, -g.y * slope, 1.0));""",
                 dict(inputs, WH=wh, NSL=scalar(mat, "NormalSlope", 1.0)),
                 unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                 {k: (unreal.CustomMaterialOutputType.CMOT_FLOAT3
                      if k in ("P", "N", "N2", "N3") else unreal.CustomMaterialOutputType.CMOT_FLOAT1)
                  for k in dict(inputs, WH=wh, NSL=wh)})
    MEL.connect_material_property(nrm, "", unreal.MaterialProperty.MP_NORMAL)

    # ③ 颜色 / 反射 / 透明度：与旧水面同口径（浅深配色 + 菲涅尔天空反射 + 深度淡入）
    shallow = vector(mat, "WaterColorShallow", unreal.LinearColor(0.40, 0.72, 0.72, 1.0))
    deep = vector(mat, "WaterColorDeep", unreal.LinearColor(0.09, 0.28, 0.32, 1.0))
    sd = scene_depth_node(mat, True)
    pixel = ex(mat, unreal.MaterialExpressionPixelDepth)
    sub = ex(mat, unreal.MaterialExpressionSubtract)
    MEL.connect_material_expressions(sd, "Color", sub, "A")
    MEL.connect_material_expressions(pixel, "", sub, "B")
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
    refl_cls = getattr(unreal, "MaterialExpressionReflectionVectorWS", None)
    sky = cube_param(mat, "ReflectionCubemap", CUBEMAP)
    if refl_cls:
        link_any(ex(mat, refl_cls), sky, ["UV", "UVs"])
    sky_mul = ex(mat, unreal.MaterialExpressionMultiply)
    link(sky, sky_mul, "A", "RGB")
    link(scalar(mat, "ReflectionStrength", 0.9), sky_mul, "B")
    emis = ex(mat, unreal.MaterialExpressionMultiply)
    link(sky_mul, emis, "A")
    link(fres, emis, "B")
    crest = ex(mat, unreal.MaterialExpressionClamp)
    link(height, crest, "")
    crest_boost = ex(mat, unreal.MaterialExpressionMultiply)
    link(crest, crest_boost, "A")
    link(scalar(mat, "CrestFoam", 0.35), crest_boost, "B")
    emis_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(emis, emis_sum, "A")
    link(crest_boost, emis_sum, "B")
    MEL.connect_material_property(emis_sum, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    op_base = ex(mat, unreal.MaterialExpressionMultiply)
    link(scalar(mat, "OpacityBase", 0.30), op_base, "A")
    link(fade, op_base, "B")
    op_fres = ex(mat, unreal.MaterialExpressionMultiply)
    link(fres, op_fres, "A")
    link(scalar(mat, "FresnelOpacity", 0.25), op_fres, "B")
    op_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(op_base, op_sum, "A")
    link(op_fres, op_sum, "B")
    op_cl = ex(mat, unreal.MaterialExpressionClamp)
    link(op_sum, op_cl, "")
    max_mode = getattr(unreal.ClampMode, "CMODE_CLAMP_MAX", None)
    if max_mode is not None:
        op_cl.set_editor_property("clamp_mode", max_mode)
    op_cl.set_editor_property("max_default", 0.5)
    MEL.connect_material_property(op_cl, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(scalar(mat, "Roughness", 0.05), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(scalar(mat, "Specular", 1.0), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.connect_material_property(scalar(mat, "Metallic", 0.0), "", unreal.MaterialProperty.MP_METALLIC)

    errs = MEL.recompile_material(mat)
    log("wave water recompile -> %s" % errs)
    log("wave water expressions: %d" % len(MEL.get_material_expressions(mat) or []))
    save_fresh(mat, WAVE_MAT, "M_FountainWaveWater")
    return mat


def build_hidden_material():
    """把主网格里旧的**平面水体**藏掉（Masked + OpacityMask=0，直接剔除像素，零绘制成本）。"""
    mat = ensure_asset(HIDDEN_MAT, unreal.Material, unreal.MaterialFactoryNew)
    if not mat or (MEL.get_material_expressions(mat) or []):
        return mat
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    zero = ex(mat, unreal.MaterialExpressionConstant)
    zero.set_editor_property("r", 0.0)
    MEL.connect_material_property(zero, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    MEL.recompile_material(mat)
    save_fresh(mat, HIDDEN_MAT, "M_FountainHidden")
    return mat


def build_wave_mesh(wave_inst):
    """把 3 个**密集网格**水面盘放进独立网格（WPO 需要足够顶点才看得出起伏）。"""
    handle = SV.create_mesh().handle
    rings = 14
    for name, radius, z in (("disc_low", 182.2, WATER_LOW), ("disc_mid", 110.5, WATER_MID),
                            ("disc_top", 73.0, WATER_TOP)):
        prof = []
        for i in range(rings + 1):
            prof.append((radius * i / rings, z))
        for i in range(rings, -1, -1):
            prof.append((radius * i / rings, z - 3.0))
        pts = [unreal.Vector2D(r * SCALE, zz * SCALE) for (r, zz) in prof]
        res = SV.append_revolve_polygon(handle, tf(), pts, 0.0, 96, 360.0, 0)
        ok = getattr(res, "success", None)
        LOG.append(("wave_" + name, ok))
        log("wave piece %-10s rings=%d r=%.1f z=%.1f %s" % (name, rings, radius, z, ok))
    info = SV.get_mesh_info(handle)
    log("wave mesh: tris=%d comps=%d open_edges=%d" % (
        info.triangle_count, info.connected_components, info.open_border_edges))
    check("wave_mesh_closed", info.open_border_edges == 0)
    SV.save_mesh_to_static_mesh(handle, WAVE_MESH, True, True, False, True)
    SV.release_mesh(handle)
    time.sleep(1.0)
    m = unreal.load_asset(WAVE_MESH)
    if m and wave_inst:
        slots = list(m.get_editor_property("static_materials") or [])
        while len(slots) < 1:
            slots.append(unreal.StaticMaterial())
        slots[0].set_editor_property("material_interface", wave_inst)
        m.set_editor_property("static_materials", slots)
        m.modify()
        EAL.save_loaded_asset(m, True)
    stamp = save_fresh(unreal.load_asset(WAVE_MESH), WAVE_MESH, "SM_RomanFountain_WaterWaves")
    m = unreal.load_asset(WAVE_MESH)
    bb = m.get_bounds()
    slot_names = [m.get_material(i).get_name() if m.get_material(i) else "None"
                  for i in range(len(m.get_editor_property("static_materials") or []))]
    log("wave mesh readback: tris=%d bbox %.0fx%.0fx%.0f origin_z=%.1f slots=%s" % (
        m.get_num_triangles(0), bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2,
        bb.origin.z, slot_names))
    check("wave_mesh_saved", bool(stamp))
    return m


def build_cascade_material():
    """水帘专用材质：**程序化竖向条纹** + 泡沫贴图，滚动方向沿柱面 v（向下）。

    为什么单独做：旧水帘用 `M_FountainWaterFilm` 的"两张泡沫贴图相乘"，若贴图本身对比度低就几乎看不出流动
    （用户反馈"像固体、没有流动感"）。这里把流动做成 **sin 条纹 + 泡沫贴图** 叠加，条纹是确定可见的，
    且同样用自算柱面 UV（不依赖网格 UV/切线）。新建资产名，避免重建已被网格引用的旧材质（会触发 !IsRooted 断言）。
    """
    mat = ensure_asset(CASCADE_MAT, unreal.Material, unreal.MaterialFactoryNew)
    if not mat or (MEL.get_material_expressions(mat) or []):
        log("cascade material exists or unavailable - skip rebuild")
        return mat
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)

    pos = ex(mat, POS_CLS)
    scale = scalar(mat, "SheetScale", 200.0)
    around = scalar(mat, "AroundRepeat", 26.0)
    uv = custom(mat, """
float r = max(length(P.xy), 0.1);
float u = atan2(P.y, P.x) * 0.159154943;
float v = -P.z / max(S, 0.001);
return float2(u * AR, v);""",
                {"P": pos, "S": scale, "AR": around},
                unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                {"P": unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                 "S": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                 "AR": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    speed = scalar(mat, "FlowSpeed", 1.1)
    t = ex(mat, unreal.MaterialExpressionTime)
    ts = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, ts, "A")
    link(speed, ts, "B")
    flow_uv = custom(mat, "return UV + float2(0.0, T);", {"UV": uv, "T": ts},
                     unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                     {"UV": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                      "T": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    # ① 程序化条纹（确定可见的向下流动）
    bands = scalar(mat, "BandCount", 9.0)
    band_amp = scalar(mat, "BandStrength", 0.55)
    proc = custom(mat, """
float s = sin(UV.y * BC * 6.2831853 + sin(UV.x * 0.7 + UV.y * 1.3) * 1.2);
return saturate(0.5 + 0.5 * s * Amp);""",
                  {"UV": flow_uv, "BC": bands, "Amp": band_amp},
                  unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                  {"UV": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                   "BC": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                   "Amp": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    # ② 泡沫贴图（有对比度就叠加，没有也不影响条纹）
    foam_tex = texture_param(mat, "FoamTexture", T_FOAM_FALL)
    link_any(flow_uv, foam_tex, ["UVs", "UV"])
    foam_mul = ex(mat, unreal.MaterialExpressionMultiply)
    link(proc, foam_mul, "A")
    link(foam_tex, foam_mul, "B", "R")
    foam_amp = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam_mul, foam_amp, "A")
    link(scalar(mat, "FoamStrength", 1.6), foam_amp, "B")
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
    link(scalar(mat, "EmissiveGain", 0.95), emis, "B")
    MEL.connect_material_property(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    op_base = scalar(mat, "OpacityBase", 0.45)
    op_foam = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam_cl, op_foam, "A")
    link(scalar(mat, "OpacityFoam", 0.45), op_foam, "B")
    op_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(op_base, op_sum, "A")
    link(op_foam, op_sum, "B")
    op_cl = ex(mat, unreal.MaterialExpressionClamp)
    link(op_sum, op_cl, "")
    max_mode = getattr(unreal.ClampMode, "CMODE_CLAMP_MAX", None)
    if max_mode is not None:
        op_cl.set_editor_property("clamp_mode", max_mode)
    op_cl.set_editor_property("max_default", 0.9)
    MEL.connect_material_property(op_cl, "", unreal.MaterialProperty.MP_OPACITY)
    errs = MEL.recompile_material(mat)
    log("cascade recompile -> %s" % errs)
    save_fresh(mat, CASCADE_MAT, "M_FountainCascadeFlow")
    return mat


def fix_water_material(mat):
    """只改属性：光照模式 / SceneDepth 节点 id / 透明度上限。不碰表达式表。"""
    tlm = getattr(unreal.TranslucencyLightingMode, "TLM_SURFACE_PER_PIXEL_LIGHTING", None)
    if tlm is not None:
        mat.set_editor_property("translucency_lighting_mode", tlm)
        check("water_tlm_surface_per_pixel",
              mat.get_editor_property("translucency_lighting_mode") == tlm)
    else:
        check("water_tlm_surface_per_pixel", False)
    log("water tlm = %s" % mat.get_editor_property("translucency_lighting_mode"))

    # 关键：本工程网格走 XAtlas，**切线基不可控**（锥面/圆盘的 UV 岛方向随机），
    # 法线贴图/法线扰动在切线空间里可能完全看不出效果 → 水面像一块没起伏的板。
    # 水面都是水平盘面，所以直接把法线当**世界空间**用（材质里给的 (x,y,1) 就是世界空间的向上法线）。
    try:
        mat.set_editor_property("tangent_space_normal", False)
        check("water_world_space_normal", mat.get_editor_property("tangent_space_normal") is False)
        log("tangent_space_normal = %s" % mat.get_editor_property("tangent_space_normal"))
    except Exception as exc:  # noqa: BLE001
        log("tangent_space_normal 设置失败: %s" % exc)
        check("water_world_space_normal", False)

    depth_enum = getattr(unreal.SceneTextureId, "PPI_SCENE_DEPTH", None)
    fixed_scene = 0
    for e in (MEL.get_material_expressions(mat) or []):
        if "SceneTexture" not in e.get_class().get_name():
            continue
        if depth_enum is not None:
            e.set_editor_property("scene_texture_id", depth_enum)
        log("SceneTexture id = %s" % e.get_editor_property("scene_texture_id"))
        fixed_scene += 1
    check("water_scene_depth_nodes", fixed_scene >= 1)

    # 接在 Opacity 上的那个 Clamp：把上限压到 0.62，避免掠射角读成实心板
    try:
        op_node = MEL.get_material_property_input_node(mat, unreal.MaterialProperty.MP_OPACITY)
        if op_node and "Clamp" in op_node.get_class().get_name():
            # 本版 ClampMode 只有 CMODE_CLAMP / CMODE_CLAMP_MAX / CMODE_CLAMP_MIN（探针读出），
            # 没有 MinMax；透明度各项恒非负，所以 CLAMP_MAX(0.62) 等价于 [0, 0.62]。
            mode = None
            for cand in ("CMODE_CLAMP_MAX", "CMODE_CLAMP"):
                mode = getattr(unreal.ClampMode, cand, None)
                if mode is not None:
                    break
            if mode is not None:
                op_node.set_editor_property("clamp_mode", mode)
            op_node.set_editor_property("max_default", 0.5)
            log("opacity clamp max = %s (mode %s)" % (
                op_node.get_editor_property("max_default"), op_node.get_editor_property("clamp_mode")))
            check("water_opacity_cap", abs(op_node.get_editor_property("max_default") - 0.5) < 0.01)
        else:
            check("water_opacity_cap", False)
    except Exception as exc:  # noqa: BLE001
        log("opacity clamp fix failed: %s" % exc)
        check("water_opacity_cap", False)

    errs = MEL.recompile_material(mat)
    log("water recompile (property-only) -> %s" % errs)
    save_fresh(mat, WATER_MAT, "M_FountainWater")
    return mat


def build_water_material():
    """工程自制水面材质：极坐标双层滚动法线 + 落水驱动的解析涟漪 + 场景深度配色 + 菲涅尔天空反射。

    为什么不用包内 `M_Water_Clean` 实例：那套材质在 XAtlas UV 上滚法线，尺度不可控、又偏暗，
    实测读成"深色固体"。这里把法线/涟漪全部放在自算的极坐标上，并按场景深度做浅→深过渡。

    **已存在时走"只改属性"路径**：重建表达式表会被断言 !IsRooted() 杀掉进程
    （材质被已保存的网格/实例引用，连删掉实例都不够——被删对象在 GC 前仍持有引用）。
    本轮要修的三件事全是属性，不需要动图：
      ① 材质光照模式 → TLM_SURFACE_PER_PIXEL_LIGHTING（默认 Volumetric NonDirectional 收不到直射光）
      ② SceneTexture 节点 id → PPI_SCENE_DEPTH（建图时写错枚举名，静默退回 SceneColor）
      ③ 接在 Opacity 上的 Clamp 的 Max → 0.62（避免掠射角变成实心板）
    """
    mat = ensure_asset(WATER_MAT, unreal.Material, unreal.MaterialFactoryNew)
    if not mat:
        check("water_material_created", False)
        return None
    check("water_material_created", True)
    if MEL.get_material_expressions(mat) or []:
        return fix_water_material(mat)
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("two_sided", True)
    # 关键：半透明 Default Lit 的默认光照模式是 Volumetric NonDirectional，几乎收不到直射太阳光 →
    # 水面会读成"没有光的暗板/固体"。水/海面必须用 Surface Per Pixel。
    tlm = None
    # 真实枚举名（探针读出）：TLM_SURFACE_PER_PIXEL_LIGHTING
    for cand in ("TLM_SURFACE_PER_PIXEL_LIGHTING", "TLM_SURFACE"):
        tlm = getattr(unreal.TranslucencyLightingMode, cand, None)
        if tlm is not None:
            break
    if tlm is not None:
        mat.set_editor_property("translucency_lighting_mode", tlm)
        log("translucency_lighting_mode = %s" % tlm)
    else:
        log("WARN: 找不到 SurfacePerPixel 光照模式枚举，水面可能只吃间接光")

    pos = ex(mat, POS_CLS)
    scale = scalar(mat, "FountainScale", SCALE)
    # --- 极坐标 UV（1× 单位）：u=半径、v=半径×角度 —— 世界等比例，中心畸变被中央基座挡住
    polar = custom(mat, """
float r = max(length(P.xy), 0.0) / max(FS, 0.001);
float th = atan2(P.y, P.x) * 0.159154943;
return float2(r, r * th * 6.2831853);""",
                   {"P": pos, "FS": scale}, unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                   {"P": unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                    "FS": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    wt = ex(mat, unreal.MaterialExpressionMultiply)
    link(ex(mat, unreal.MaterialExpressionTime), wt, "A")
    speed = scalar(mat, "WaveSpeed", 0.05)
    link(speed, wt, "B")
    uv1 = custom(mat, """
float2 uv = P / max(WS, 0.001);
uv.x -= T;
return uv;""",
                 {"P": polar, "WS": scalar(mat, "WaveScale", 150.0), "T": wt},
                 unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                 {"P": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                  "WS": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                  "T": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    wt2 = ex(mat, unreal.MaterialExpressionMultiply)
    link(ex(mat, unreal.MaterialExpressionTime), wt2, "A")
    speed2 = scalar(mat, "Wave2Speed", 0.09)
    link(speed2, wt2, "B")
    uv2 = custom(mat, """
float2 uv = P / max(WS, 0.001);
uv.x -= T;
return uv * 1.37 + float2(0.21, 0.57);""",
                 {"P": polar, "WS": scalar(mat, "Wave2Scale", 62.0), "T": wt2},
                 unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                 {"P": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                  "WS": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                  "T": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    n1 = texture_param(mat, "NormalTex", WAVE_NORMAL_A)
    link_any(uv1, n1, ["UVs", "UV"])
    n2 = texture_param(mat, "NormalTex2", WAVE_NORMAL_B)
    link_any(uv2, n2, ["UVs", "UV"])

    # --- 落水驱动的解析涟漪：在每个落点半径上生成向外的波列（双环，衰减）
    ripple = custom(mat, """
float r = length(P.xy) / max(FS, 0.001);
float acc = 0.0;
float R[2] = { RA, RB };
for (int i = 0; i < 2; ++i)
{
    float d = r - R[i];
    float u = d * 6.2831853 / max(Lam, 0.001) - T * Freq * 6.2831853;
    acc += sin(u) * exp(-abs(d) / max(Width, 0.001));
}
return acc;""",
                     {"P": pos, "FS": scale, "RA": scalar(mat, "RippleRadiusA", 92.0),
                      "RB": scalar(mat, "RippleRadiusB", 137.0), "Lam": scalar(mat, "RippleLambda", 78.0),
                      "Freq": scalar(mat, "RippleFreq", 0.45), "T": ex(mat, unreal.MaterialExpressionTime),
                      "Width": scalar(mat, "RippleWidth", 210.0)},
                     unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                     {"P": unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                      "FS": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                      "RA": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                      "RB": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                      "Lam": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                      "Freq": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                      "T": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                      "Width": unreal.CustomMaterialOutputType.CMOT_FLOAT1})

    # --- 法线合成：两层波浪 + 涟漪扰动
    normal = custom(mat, """
float2 xy = (N1 - 0.5) * 2.0 * S1 + (N2 - 0.5) * 2.0 * S2;
float2 dir = length(P.xy) > 0.01 ? normalize(P.xy) : float2(0, 1);
xy += dir * Ripple * RS;
return normalize(float3(xy, 1.0));""",
                    {"N1": n1, "N2": n2, "P": pos, "Ripple": ripple,
                     "S1": scalar(mat, "NormalStrength", 0.55), "S2": scalar(mat, "NormalStrength2", 0.35),
                     "RS": scalar(mat, "RippleStrength", 0.45)},
                    unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                    {"N1": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                     "N2": unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                     "P": unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                     "Ripple": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                     "S1": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                     "S2": unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                     "RS": unreal.CustomMaterialOutputType.CMOT_FLOAT1})
    MEL.connect_material_property(normal, "", unreal.MaterialProperty.MP_NORMAL)

    # --- 场景深度：浅（透、亮）→ 深（暗、实）
    sd = scene_depth_node(mat, True)
    try:
        log("scene_texture_id = %s" % sd.get_editor_property("scene_texture_id"))
    except Exception as exc:  # noqa: BLE001
        log("scene_texture_id readback failed: %s" % exc)
    pixel = ex(mat, unreal.MaterialExpressionPixelDepth)
    sub = ex(mat, unreal.MaterialExpressionSubtract)
    if not MEL.connect_material_expressions(sd, "Color", sub, "A"):
        log("SceneTexture Color -> Subtract.A failed")
    MEL.connect_material_expressions(pixel, "", sub, "B")
    div = ex(mat, unreal.MaterialExpressionDivide)
    link(sub, div, "A")
    link(scalar(mat, "DepthScale", 190.0), div, "B")
    fade = ex(mat, unreal.MaterialExpressionClamp)
    link(div, fade, "")

    shallow = vector(mat, "WaterColorShallow", unreal.LinearColor(0.40, 0.72, 0.72, 1.0))
    deep = vector(mat, "WaterColorDeep", unreal.LinearColor(0.09, 0.28, 0.32, 1.0))
    col = ex(mat, unreal.MaterialExpressionLinearInterpolate)
    link(shallow, col, "A")
    link(deep, col, "B")
    link(fade, col, "Alpha")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)

    # --- 菲涅尔天空反射（立方图）：把"像水"最关键的一层高光/反射补上
    fres = ex(mat, unreal.MaterialExpressionFresnel)
    link(scalar(mat, "FresnelPower", 3.5), fres, "ExponentIn")
    refl_cls = getattr(unreal, "MaterialExpressionReflectionVectorWS", None)
    refl = ex(mat, refl_cls) if refl_cls else None
    sky = cube_param(mat, "ReflectionCubemap", CUBEMAP)
    if refl is not None:
        link_any(refl, sky, ["UV", "UVs"])
    else:
        log("ReflectionVectorWS 不存在 —— 天空反射这一层先用常量（不影响其余水效）")
    sky_scale = ex(mat, unreal.MaterialExpressionMultiply)
    link(sky, sky_scale, "A", "RGB")
    link(scalar(mat, "ReflectionStrength", 0.75), sky_scale, "B")
    emis = ex(mat, unreal.MaterialExpressionMultiply)
    link(sky_scale, emis, "A")
    link(fres, emis, "B")
    # 波峰泡沫：涟漪正向部分提亮（模拟水花推开的白沫）
    crest = ex(mat, unreal.MaterialExpressionClamp)
    link(ripple, crest, "")
    crest_mul = ex(mat, unreal.MaterialExpressionMultiply)
    link(crest, crest_mul, "A")
    link(scalar(mat, "RippleFoam", 0.45), crest_mul, "B")
    # 与立方图无关的"天空底色"：即使反射贴图偏暗，水面也永远有一点天光，不会读成黑板
    sky_tint = vector(mat, "SkyTint", unreal.LinearColor(0.55, 0.72, 0.82, 1.0))
    sky_amb = ex(mat, unreal.MaterialExpressionMultiply)
    link(sky_tint, sky_amb, "A")
    link(scalar(mat, "SkyAmbient", 0.14), sky_amb, "B")
    emis_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(emis, emis_sum, "A")
    link(crest_mul, emis_sum, "B")
    emis_sum2 = ex(mat, unreal.MaterialExpressionAdd)
    link(emis_sum, emis_sum2, "A")
    link(sky_amb, emis_sum2, "B")
    MEL.connect_material_property(emis_sum2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    op = ex(mat, unreal.MaterialExpressionMultiply)
    link(scalar(mat, "OpacityBase", 0.42), op, "A")
    link(fade, op, "B")
    op2 = ex(mat, unreal.MaterialExpressionMultiply)
    link(fres, op2, "A")
    link(scalar(mat, "FresnelOpacity", 0.5), op2, "B")
    op_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(op, op_sum, "A")
    link(op2, op_sum, "B")
    op_crest = ex(mat, unreal.MaterialExpressionMultiply)
    link(crest, op_crest, "A")
    link(scalar(mat, "RippleFoamOpacity", 0.35), op_crest, "B")
    op_sum2 = ex(mat, unreal.MaterialExpressionAdd)
    link(op_sum, op_sum2, "A")
    link(op_crest, op_sum2, "B")
    op_cl = ex(mat, unreal.MaterialExpressionClamp)
    link(op_sum2, op_cl, "")
    link_any(scalar(mat, "MaxOpacity", 0.62), op_cl, ["Max"])
    MEL.connect_material_property(op_cl, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(scalar(mat, "Roughness", 0.06), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(scalar(mat, "Specular", 1.0), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.connect_material_property(scalar(mat, "Metallic", 0.0), "", unreal.MaterialProperty.MP_METALLIC)

    errs = MEL.recompile_material(mat)
    log("water recompile -> %s" % errs)
    exprs = MEL.get_material_expressions(mat) or []
    log("water expressions: %d" % len(exprs))
    for prop, label in ((unreal.MaterialProperty.MP_BASE_COLOR, "BaseColor"),
                        (unreal.MaterialProperty.MP_OPACITY, "Opacity"),
                        (unreal.MaterialProperty.MP_NORMAL, "Normal"),
                        (unreal.MaterialProperty.MP_EMISSIVE_COLOR, "Emissive")):
        try:
            node = MEL.get_material_property_input_node(mat, prop)
            log("%s <- %s" % (label, node.get_class().get_name() if node else "None"))
        except Exception as exc:  # noqa: BLE001
            log("%s readback failed: %s" % (label, exc))
    check("water_material_expressions", len(exprs) >= 25)
    save_fresh(mat, WATER_MAT, "M_FountainWater")
    return mat


def make_instance(path, parent, scalars=None, vectors=None, textures=None):
    inst = ensure_asset(path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew)
    if not inst:
        check("instance_" + path.rsplit("/", 1)[-1], False)
        return None
    MEL.set_material_instance_parent(inst, parent)
    for name, value in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(inst, name, value)
    for name, value in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(inst, name, value)
    for name, tex_path in (textures or {}).items():
        tex = unreal.load_asset(tex_path)
        if tex:
            MEL.set_material_instance_texture_parameter_value(inst, name, tex)
    MEL.update_material_instance(inst)
    save_fresh(inst, path, path.rsplit("/", 1)[-1])
    return inst


# ------------------------------------------------------------------ 4. 几何
def build_fx_mesh(film_foam, film_wet, cascade, caustics):
    dm = SV.create_mesh()
    handle = dm.handle
    made = 0
    for name, mat_id, steps, profile in PIECES:
        # 环形薄壁：剖面必须自己闭合（本 API 只在 r=0 接触轴时天然闭合）
        loop = list(profile)
        if loop[0] != loop[-1]:
            loop.append(loop[0])
        pts = [unreal.Vector2D(r * SCALE, z * SCALE) for (r, z) in loop]
        res = SV.append_revolve_polygon(handle, tf(), pts, 0.0, steps, 360.0, mat_id)
        ok = getattr(res, "success", None)
        LOG.append(("piece_" + name, ok))
        log("piece %-22s steps=%3d mat=%d %s" % (name, steps, mat_id, ok))
        if ok:
            made += 1
    info = SV.get_mesh_info(handle)
    log("fx mesh: tris=%d comps=%d open_edges=%d bbox %.0f x %.0f x %.0f (pieces=%d/%d)" % (
        info.triangle_count, info.connected_components, info.open_border_edges,
        info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
        info.bounds_max.z - info.bounds_min.z, made, len(PIECES)))
    check("fx_all_pieces", made == len(PIECES))
    check("fx_closed", info.open_border_edges == 0)
    check("fx_components", info.connected_components == len(PIECES))
    SV.save_mesh_to_static_mesh(handle, FX, True, True, False, True)
    SV.release_mesh(handle)
    time.sleep(1.0)
    # 直接写 static_materials（set_asset_materials 在新网格上没落槽，这里显式按槽号赋值）
    mesh0 = unreal.load_asset(FX)
    slots = list(mesh0.get_editor_property("static_materials") or [])
    wanted = [film_foam, film_wet, cascade, caustics]
    while len(slots) < len(wanted):
        slots.append(unreal.StaticMaterial())
    for i, mat in enumerate(wanted):
        if mat:
            slots[i].set_editor_property("material_interface", mat)
    mesh0.set_editor_property("static_materials", slots)
    mesh0.modify()
    EAL.save_loaded_asset(mesh0, True)
    stamp = save_fresh(unreal.load_asset(FX), FX, "SM_RomanFountain_WaterFX")
    mesh = unreal.load_asset(FX)
    bb = mesh.get_bounds()
    slots = [mesh.get_material(i).get_name() if mesh.get_material(i) else "None"
             for i in range(len(mesh.get_editor_property("static_materials") or []))]
    log("fx readback: bbox %.0f x %.0f x %.0f origin z=%.1f tris=%d slots=%s" % (
        bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2, bb.origin.z,
        mesh.get_num_triangles(0), slots))
    check("fx_slots_4", len(slots) == 4)
    check("fx_saved", bool(stamp))
    return mesh


# ------------------------------------------------------------------ run
film_mat = build_film_material()
# 水面实例换父级（v5 的包内实例读成深色固体）：**先删实例**再重建材质，保证重建时材质无人引用
water_inst_path = MATDIR + "/MIC_FountainWater"
if EAL.does_asset_exist(water_inst_path):
    EAL.delete_asset(water_inst_path)
    log("removed v5 MIC_FountainWater (读成深色固体的包内实例)")
water_mat = build_water_material()
cascade_flow_mat = build_cascade_material()
cascade_flow = make_instance(CASCADE_INST, cascade_flow_mat,
                             {"SheetScale": 200.0, "AroundRepeat": 26.0,
                              "BandCount": 9.0, "BandStrength": 0.5, "FlowSpeed": 1.1,
                              "FoamStrength": 1.7, "EmissiveGain": 1.0,
                              "OpacityBase": 0.45, "OpacityFoam": 0.45},
                             {"SheetColor": unreal.LinearColor(0.70, 0.85, 0.90, 1.0)},
                             {"FoamTexture": T_FOAM_FALL})
film_foam = make_instance(MATDIR + "/MIC_FountainFoam", film_mat,
                          {"FoamSize": 55.0, "FoamSpeed": 0.02, "FoamSpeed2": 0.035,
                           "FoamIntensity": 1.9, "FoamContrast": 1.5,
                           "OpacityBase": 0.5, "OpacityFoam": 0.55, "FresnelPower": 4.0, "FresnelBoost": 0.3,
                           },
                          {"FilmColor": unreal.LinearColor(0.94, 0.97, 0.99, 1.0)},
                          {"FoamTexture": T_FOAM_EDGE, "FoamTexture2": T_FOAM_EDGE})
film_wet = make_instance(MATDIR + "/MIC_FountainWet", film_mat,
                         {"FoamSize": 90.0, "FoamSpeed": 0.012, "FoamSpeed2": 0.02,
                          "FoamIntensity": 0.35, "FoamContrast": 2.2,
                          "OpacityBase": 0.34, "OpacityFoam": 0.16, "FresnelPower": 2.5, "FresnelBoost": 0.55,
                          },
                         {"FilmColor": unreal.LinearColor(0.15, 0.17, 0.18, 1.0)},
                         {"FoamTexture": T_FOAM_POND, "FoamTexture2": T_FOAM_POND})
cascade = make_instance(MATDIR + "/MIC_FountainCascade", film_mat,
                        {"FoamSize": 34.0, "FoamSpeed": 0.42, "FoamSpeed2": 0.68,
                         "FoamIntensity": 2.2, "FoamContrast": 1.25,
                         "OpacityBase": 0.78, "OpacityFoam": 0.3, "FresnelPower": 3.0, "FresnelBoost": 0.25,
                         },
                        {"FilmColor": unreal.LinearColor(0.94, 0.97, 0.99, 1.0)},
                        {"FoamTexture": T_FOAM_FALL, "FoamTexture2": T_FOAM_FALL})
caustics = make_instance(MATDIR + "/MIC_FountainCaustics", unreal.load_asset(CAUSTICS),
                         {"Speed": 0.35, "SamplingScale": 1.6},
                         {"Colour": unreal.LinearColor(0.42, 0.68, 0.66, 1.0)})
# 旧的"平面水"实例不再使用（主网格 slot1 会被隐藏材质接管，水面改由会起伏的 WaterWaves 网格承担）
water = None

# 会真正起伏的水面：材质 + 实例 + 密集网格
hidden_mat = build_hidden_material()
wave_mat = build_wave_water_material()
if EAL.does_asset_exist(WAVE_INST):
    EAL.delete_asset(WAVE_INST)
wave_inst = make_instance(WAVE_INST, wave_mat,
                          {"FountainScale": SCALE, "DepthScale": 190.0,
                           # 第一版 7 cm 起伏放在 7 m 水盘上"看不出来"（用户实测反馈），这轮先调到一眼可见，
                           # 观感过强时只降 WaveHeight 一个数即可。
                           "WaveHeight": 22.0, "NormalSlope": 1.6,
                           "Wave1Length": 240.0, "Wave1Speed": 0.5, "Wave1Amp": 0.7,
                           "Wave2Length": 140.0, "Wave2Speed": 0.8, "Wave2Amp": 0.5,
                           "NoiseScale": 240.0, "NoiseSpeed": 0.4, "NoiseStrength": 0.6, "NoiseDelta": 5.0,
                           "RippleRadiusA": 92.0, "RippleRadiusB": 137.0, "RippleLambda": 78.0,
                           "RippleFreq": 0.6, "RippleWidth": 260.0, "RippleStrength": 1.4,
                           "OpacityBase": 0.34, "FresnelOpacity": 0.30, "FresnelPower": 3.0,
                           "ReflectionStrength": 0.9, "CrestFoam": 0.5,
                           "Roughness": 0.05, "Specular": 1.0, "Metallic": 0.0},
                          {"WaterColorShallow": unreal.LinearColor(0.40, 0.72, 0.72, 1.0),
                           "WaterColorDeep": unreal.LinearColor(0.09, 0.28, 0.32, 1.0)},
                          {"NoiseTex": T_NOISE, "NoiseTex2": T_NOISE, "NoiseTex3": T_NOISE,
                           "ReflectionCubemap": CUBEMAP})
log("noise texture: %s" % T_NOISE)

# 实例参数读回（UE 5.8 的 set_* 常常返回 False 但实际写进去了，所以按"写入值是否落在实例上"判断）
for inst, label in ((water, "MIC_FountainWater"), (caustics, "MIC_FountainCaustics"),
                    (film_foam, "MIC_FountainFoam"), (film_wet, "MIC_FountainWet"),
                    (cascade, "MIC_FountainCascade")):
    if not inst:
        continue
    try:
        scal = inst.get_editor_property("scalar_parameter_values")
        vecs = inst.get_editor_property("vector_parameter_values")
        texs = inst.get_editor_property("texture_parameter_values")
        log("%s overrides: scalar=%d vector=%d texture=%d" % (
            label, len(scal or []), len(vecs or []), len(texs or [])))
        names = [str(v.get_editor_property("parameter_info").get_editor_property("name")) for v in (scal or [])]
        if names:
            log("   scalars: %s" % ", ".join(names[:16]))
    except Exception as exc:  # noqa: BLE001
        log("%s readback failed: %s" % (label, exc))

if film_mat and film_foam and film_wet and caustics:
    build_fx_mesh(film_foam, film_wet, cascade_flow or cascade, caustics)

if wave_inst:
    build_wave_mesh(wave_inst)

# 主网格 slot1 → 隐藏材质（旧的平面水体剔除；slot0 大理石不动）
if hidden_mat:
    SV.set_asset_materials(FULL, "%s,%s" % (MARBLE, HIDDEN_MAT), True)
    EAL.save_loaded_asset(unreal.load_asset(FULL), True)
    stamp = save_fresh(unreal.load_asset(FULL), FULL, "SM_RomanFountain_20")
    mesh = unreal.load_asset(FULL)
    slots = [mesh.get_material(i).get_name() if mesh.get_material(i) else "None"
             for i in range(len(mesh.get_editor_property("static_materials") or []))]
    bb = mesh.get_bounds()
    log("fountain readback: bbox %.0f x %.0f x %.0f tris=%d slots=%s" % (
        bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2,
        mesh.get_num_triangles(0), slots))
    check("fountain_slot1_hidden", bool(slots) and "M_FountainHidden" in (slots[-1] or ""))
    check("fountain_bbox_unchanged", abs(bb.box_extent.x * 2 - 960) < 1 and abs(bb.box_extent.z * 2 - 720) < 1)
    # 旧平面水实例已无人引用 → 清掉，避免面板/编辑器里出现两个"水面"
    if EAL.does_asset_exist(water_inst_path):
        EAL.delete_asset(water_inst_path)
        log("removed obsolete %s（被 WaterWaves 取代）" % water_inst_path)

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
