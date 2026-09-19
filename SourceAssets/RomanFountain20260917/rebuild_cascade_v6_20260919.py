"""水帘 V6：V4/V5 的 streak 场算出来却**没接到输出**（V3 是靠 foam_mul=proc×foam 接的）→
画面只剩低频泡沫层（V5 列尺度太低 = 平板）。V6 = V5 + streak 接入颜色/不透明链：
foam_total = saturate(streak*0.85 + foam_cl*0.9)。

水帘 V5：V4 的谐波（绕圈 4–31 周）频率太低 → 平滑大 blob 且 4 周主频读作"四个重复扇区"。
V5 = 26 条清晰基带 × **逐列噪声调制**（相位/宽度/亮度每列不同 → 打散"开箱复制"观感）；
噪声/泡沫的 u 采样用非整数列尺度（相邻列取到不同噪声；唯一不连续缝落在背面子午线）。
流向沿用 V4 约定：所有含 T 相位 = (v·b − T·c), b,c>0 → 向下（已用慢动作互相关证明 dy=+39px）。
新资产 M_FountainCascadeFlowV5 + MIC 换父级（参数名保持一致）。
"""

import os
import time
import unreal

MATDIR = "/Game/Props/RomanFountain20260917/Materials"
CASCADE5 = MATDIR + "/M_FountainCascadeFlowV6"
PACK = "/Game/WaterMaterials"
T_FOAM_FALL = PACK + "/Textures/T_Waterfall_Foam_Directional"
NOISE_CANDIDATES = (PACK + "/Textures/T_Noises", PACK + "/Textures/T_Noise_Progressive",
                    PACK + "/Textures/T_Noise_Curves",
                    PACK + "/Textures/T_Ocean_EdgeFoam")
T_NOISE = next((p for p in NOISE_CANDIDATES if unreal.load_asset(p)), NOISE_CANDIDATES[0])

STARTED = time.time()
LOG = []
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary


def log(m):
    print("[cv5] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-30s %s" % (label, "OK" if ok else "FAIL"))
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
    log("saved %-30s STALE" % label)
    return disk(path)


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


def custom(mat, code, inputs, output_type=None):
    n = ex(mat, unreal.MaterialExpressionCustom)
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
    wp = ex(mat, unreal.MaterialExpressionWorldPosition)
    op = ex(mat, unreal.MaterialExpressionObjectPositionWS)
    sub = ex(mat, unreal.MaterialExpressionSubtract)
    link(wp, sub, "A")
    link(op, sub, "B")
    return sub


def build_cascade6():
    mat = EAL.load_asset(CASCADE5) or unreal.load_asset(CASCADE5)
    if not mat:
        folder, name = CASCADE5.rsplit("/", 1)
        EAL.make_directory(folder)
        mat = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if MEL.get_material_expressions(mat):
        log("cascade6 exists - skip rebuild")
        return mat
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)

    pos = local_pos(mat)
    scale = scalar(mat, "SheetScale", 200.0)
    around = scalar(mat, "AroundRepeat", 26.0)
    uv = custom(mat, """
float r = max(length(P.xy), 0.1);
float u = atan2(P.y, P.x) * 0.159154943 * AR;
float v = -P.z / max(S, 0.001);
return float2(u, v);""",
                {"P": pos, "S": scale, "AR": around},
                unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    speed = scalar(mat, "FlowSpeed", 1.5)
    t = ex(mat, unreal.MaterialExpressionTime)
    ts = ex(mat, unreal.MaterialExpressionMultiply)
    link(t, ts, "A")
    link(speed, ts, "B")
    # 逐列噪声：x 用非整数列尺度（0.23）→ 相邻基带列取到不同噪声；y 随 v 向下慢滚
    col_uv = custom(mat, "return float2(UV.x * 0.23 + 1.7, UV.y * 0.25 - T * 0.15);",
                    {"UV": uv, "T": ts},
                    unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    coln = texture_param(mat, "ColumnNoise", T_NOISE)
    link_any(col_uv, coln, ["UVs", "UV"])
    # 26 条基带：相位/宽度被列噪声抖动 → 宽窄明暗逐列不同；相位含 (v·b − T·c) → 向下
    streak = custom(mat, """
float j = CN.r - 0.5;
float j2 = CN.g - 0.5;
float ph = UV.x * 6.2831853 + UV.y * 0.9 - T * 1.0 + j * 2.6;
float w = 0.55 + 0.45 * j2;
float band = saturate(0.5 + w * sin(ph));
band = pow(band, 1.4);
float ripple = 0.5 + 0.5 * sin(UV.y * 7.0 - T * 2.6 + j * 4.0);
float bright = 0.55 + 0.9 * saturate(CN.b + 0.25);
return saturate(band * (0.7 + 0.3 * ripple) * bright);""",
                    {"UV": uv, "T": ts, "CN": coln},
                    unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    # 双尺度泡沫：u 同样非整数列尺度 → 泡沫不逐列复制；都向下滚
    foam_uv = custom(mat, "return float2(UV.x * 0.317, UV.y * 1.0 - T * 0.9);",
                     {"UV": uv, "T": ts},
                     unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    foam_tex = texture_param(mat, "FoamTexture", T_FOAM_FALL)
    link_any(foam_uv, foam_tex, ["UVs", "UV"])
    foam_uv2 = custom(mat, "return float2(UV.x * 0.131 + 0.5, UV.y * 0.55 - T * 0.55);",
                      {"UV": uv, "T": ts},
                      unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    foam_tex2 = texture_param(mat, "FoamTexture2", T_FOAM_FALL)
    link_any(foam_uv2, foam_tex2, ["UVs", "UV"])
    foam_mix = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam_tex, foam_mix, "A", "R")
    link(foam_tex2, foam_mix, "B", "R")
    foam_amp = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam_mix, foam_amp, "A")
    link(scalar(mat, "FoamStrength", 2.5), foam_amp, "B")
    foam_cl0 = ex(mat, unreal.MaterialExpressionClamp)
    link(foam_amp, foam_cl0, "")
    # streak 接入：条纹权重 + 泡沫权重 合成总花纹（V4/V5 漏接 streak 导致平板）
    sw = ex(mat, unreal.MaterialExpressionMultiply)
    link(streak, sw, "A")
    link(scalar(mat, "StreakWeight", 0.85), sw, "B")
    fw = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam_cl0, fw, "A")
    link(scalar(mat, "FoamWeight", 0.9), fw, "B")
    tot = ex(mat, unreal.MaterialExpressionAdd)
    link(sw, tot, "A")
    link(fw, tot, "B")
    foam_cl = ex(mat, unreal.MaterialExpressionClamp)
    link(tot, foam_cl, "")
    base_col = vector(mat, "SheetColor", unreal.LinearColor(0.85, 0.93, 0.97, 1.0))
    white = ex(mat, unreal.MaterialExpressionConstant3Vector)
    white.set_editor_property("constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    col = ex(mat, unreal.MaterialExpressionLinearInterpolate)
    link(base_col, col, "A")
    link(white, col, "B")
    link(foam_cl, col, "Alpha")
    emis = ex(mat, unreal.MaterialExpressionMultiply)
    link(col, emis, "A")
    link(scalar(mat, "EmissiveGain", 3.0), emis, "B")
    MEL.connect_material_property(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op_base = scalar(mat, "OpacityBase", 0.9)
    op_foam = ex(mat, unreal.MaterialExpressionMultiply)
    link(foam_cl, op_foam, "A")
    link(scalar(mat, "OpacityFoam", 0.1), op_foam, "B")
    op_sum = ex(mat, unreal.MaterialExpressionAdd)
    link(op_base, op_sum, "A")
    link(op_foam, op_sum, "B")
    op_cl = ex(mat, unreal.MaterialExpressionClamp)
    link(op_sum, op_cl, "")
    max_mode = getattr(unreal.ClampMode, "CMODE_CLAMP_MAX", None)
    if max_mode is not None:
        op_cl.set_editor_property("clamp_mode", max_mode)
    op_cl.set_editor_property("max_default", 0.95)
    MEL.connect_material_property(op_cl, "", unreal.MaterialProperty.MP_OPACITY)
    errs = MEL.recompile_material(mat)
    check("cascade6_compile", errs == [])
    log("cascade6 expressions: %d" % len(MEL.get_material_expressions(mat) or []))
    save_fresh(mat, CASCADE5, "M_FountainCascadeFlowV6")
    return mat


mat5 = build_cascade6()
mic = unreal.load_asset(MATDIR + "/MIC_FountainCascadeFlow")
if mic and mat5:
    mic.set_editor_property("parent", mat5)
    check("mic_parent_v5", mic.get_editor_property("parent") == mat5)
    for k, v in {"FlowSpeed": 1.5, "OpacityBase": 0.9, "OpacityFoam": 0.1,
                 "FoamStrength": 2.5, "EmissiveGain": 3.0, "SheetScale": 200.0,
                 "AroundRepeat": 26.0, "StreakWeight": 0.85, "FoamWeight": 0.9}.items():
        MEL.set_material_instance_scalar_parameter_value(mic, k, v)
    MEL.set_material_instance_vector_parameter_value(
        mic, "SheetColor", unreal.LinearColor(0.85, 0.93, 0.97, 1.0))
    EAL.save_loaded_asset(mic, True)
    log("mic reparented + tuned + saved")

fails = [k for k, v in LOG if not v]
log("checks=%d failed=%d %s" % (len(LOG), len(fails), fails))
log("RESULT: %s" % ("PASS" if not fails else "FAIL"))
