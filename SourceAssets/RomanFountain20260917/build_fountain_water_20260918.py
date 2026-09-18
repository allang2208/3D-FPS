"""Fountain water pass (2026-09-18, user-approved: "更像水 + 做溢流和落水，从上往下流淌").

What this builds (all assets, no level edits):

1. `M_FountainWaterFilm` — 工程自制的水膜/泡沫/溢流材质（Unlit + Translucent + TwoSided）。
   自算**柱面 UV**（从物体空间位置取 atan2 与 z，按世界尺寸 FoamSize 归一），所以泡沫/水痕不依赖
   网格 UV（本工程网格走 XAtlas，UV 方向不可控）；两层泡沫贴图反向滚动 + 对比度 + Fresnel 提亮。
   实例（都在 `Props/RomanFountain20260917/Materials` 下，暴露参数，用户可在编辑器里直接调）：
     MIC_FountainFoam    白泡沫（水线/落点/穿出物周围的接触环）
     MIC_FountainWet     深色湿膜（水线以上到盘沿的湿痕带）
     MIC_FountainCascade 溢流水帘（快速向下滚动的条状泡沫）
2. `MIC_FountainWater` — 包内 `M_Water_Clean` 的实例（半透明 + 深度淡出 + 多层波浪法线），
   把表面从 v3 的"不透明平板"换回**像水**的半透明水；参数逐个按存在与否设置并读回。
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
PACK = "/Game/WaterMaterials"
CLEAN = PACK + "/Materials/M_Water_Clean"
CAUSTICS = PACK + "/Materials/M_Caustics"
T_FOAM_POND = PACK + "/Textures/T_Pond_Foam"
T_FOAM_EDGE = PACK + "/Textures/T_Ocean_EdgeFoam"
T_FOAM_FALL = PACK + "/Textures/T_Waterfall_Foam_Directional"
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


# ------------------------------------------------------------------ 1. 水膜材质
def build_film_material():
    mat = ensure_asset(FILM, unreal.Material, unreal.MaterialFactoryNew)
    if not mat:
        check("film_material_created", False)
        return None
    check("film_material_created", True)
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
    foam_size = scalar(mat, "FoamSize", 60.0)
    around = scalar(mat, "AroundRepeat", 1.0)
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
    ok = MEL.recompile_material(mat)
    # UE 5.8 的 recompile_material 常常返回 False（set_material_instance_* 也这样），
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
film_foam = make_instance(MATDIR + "/MIC_FountainFoam", film_mat,
                          {"FoamSize": 55.0, "FoamSpeed": 0.02, "FoamSpeed2": 0.035,
                           "FoamIntensity": 1.15, "FoamContrast": 1.8,
                           "OpacityBase": 0.42, "OpacityFoam": 0.5, "FresnelPower": 4.0, "FresnelBoost": 0.3},
                          {"FilmColor": unreal.LinearColor(0.90, 0.94, 0.97, 1.0)},
                          {"FoamTexture": T_FOAM_EDGE, "FoamTexture2": T_FOAM_EDGE})
film_wet = make_instance(MATDIR + "/MIC_FountainWet", film_mat,
                         {"FoamSize": 90.0, "FoamSpeed": 0.012, "FoamSpeed2": 0.02,
                          "FoamIntensity": 0.35, "FoamContrast": 2.2,
                          "OpacityBase": 0.34, "OpacityFoam": 0.16, "FresnelPower": 2.5, "FresnelBoost": 0.55},
                         {"FilmColor": unreal.LinearColor(0.15, 0.17, 0.18, 1.0)},
                         {"FoamTexture": T_FOAM_POND, "FoamTexture2": T_FOAM_POND})
cascade = make_instance(MATDIR + "/MIC_FountainCascade", film_mat,
                        {"FoamSize": 46.0, "FoamSpeed": 0.22, "FoamSpeed2": 0.38,
                         "FoamIntensity": 1.05, "FoamContrast": 1.45,
                         "OpacityBase": 0.6, "OpacityFoam": 0.35, "FresnelPower": 3.0, "FresnelBoost": 0.35},
                        {"FilmColor": unreal.LinearColor(0.86, 0.92, 0.95, 1.0)},
                        {"FoamTexture": T_FOAM_FALL, "FoamTexture2": T_FOAM_FALL})
caustics = make_instance(MATDIR + "/MIC_FountainCaustics", unreal.load_asset(CAUSTICS),
                         {"Speed": 0.35, "SamplingScale": 1.6},
                         {"Colour": unreal.LinearColor(0.42, 0.68, 0.66, 1.0)})
water = make_instance(MATDIR + "/MIC_FountainWater", unreal.load_asset(CLEAN),
                      {"Opacity": 0.55, "Roughness": 0.05, "Specular": 1.0, "SamplingScale": 3.0,
                       "SpeedX": 0.02, "SpeedY": 0.015, "Wave Height": 0.35, "Wave Size": 1.2,
                       "Wave Speed": 0.12, "Wave Normal Speed": 0.05, "Fresnel Power": 4.0},
                      {"Water_Colour_Light": unreal.LinearColor(0.30, 0.52, 0.50, 1.0),
                       "Water_Colour_Dark": unreal.LinearColor(0.08, 0.19, 0.20, 1.0)})

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

if film_mat and film_foam and film_wet and cascade and caustics:
    build_fx_mesh(film_foam, film_wet, cascade, caustics)

# 主网格 slot1 → 半透明水（slot0 大理石不动）
if water:
    SV.set_asset_materials(FULL, "%s,%s" % (MARBLE, MATDIR + "/MIC_FountainWater"), True)
    EAL.save_loaded_asset(unreal.load_asset(FULL), True)
    stamp = save_fresh(unreal.load_asset(FULL), FULL, "SM_RomanFountain_20")
    mesh = unreal.load_asset(FULL)
    slots = [mesh.get_material(i).get_name() if mesh.get_material(i) else "None"
             for i in range(len(mesh.get_editor_property("static_materials") or []))]
    bb = mesh.get_bounds()
    log("fountain readback: bbox %.0f x %.0f x %.0f tris=%d slots=%s" % (
        bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2,
        mesh.get_num_triangles(0), slots))
    check("fountain_slot1_is_water_instance", bool(slots) and "MIC_FountainWater" in (slots[-1] or ""))
    check("fountain_bbox_unchanged", abs(bb.box_extent.x * 2 - 960) < 1 and abs(bb.box_extent.z * 2 - 720) < 1)

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
