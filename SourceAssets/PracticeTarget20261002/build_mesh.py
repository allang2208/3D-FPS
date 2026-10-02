# 训练靶程序化建模（GeometryScript，编辑器/commandlet 通用）：
# 圆环靶面（木质背板 + 红白同心环分层 + 深色靶心）+ A 字木架 + 中心木销。
# 单位 cm，Z 向上，靶面法线 +X（Actor 前向）；原点 = 地面投影中心。
# 用法：run_ue.ps1 -Script build_mesh.py   （编辑器在跑走桥接，否则无头 commandlet）
import json, math, os
import unreal

U = unreal
SRC = r"D:\FPS3D\FPSGAME\SourceAssets\PracticeTarget20261002"
OUT = "/Game/Props/PracticeTarget20261002"
MESH_NAME = "SM_PracticeTarget"

M_WOOD, M_WHITE, M_RED, M_BULL = 0, 1, 2, 3
# 材质槽绑定现成游戏材质（BaseColor+Normal+Roughness/ORM 全套贴图，2026-10-02 探针确认）：
# 木架/背板=剧院木纹(带ORM)，白环=帆布，红环=红漆，靶心=金漆（暴击区读感）。
MAT_BINDINGS = [
    "/Game/Dungeons/AnatomyTheatre20261001/Materials/M_Theatre_Wood",
    "/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Canvas",
    "/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_RedPaint",
    "/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_YellowPaint",
]
# 第一版生成的纯色材质名，绑定成功后清理。
LEGACY_MATS = [
    "M_PracticeTarget_Wood", "M_PracticeTarget_White",
    "M_PracticeTarget_Red", "M_PracticeTarget_Bull",
]

FACE_Z = 150.0          # 靶心高度
BACKER_R = 48.0         # 木质背板半径（露出木圈）
BACKER_HALF = 3.0       # 背板半厚，x -3..3

log = []


def say(msg):
    log.append(msg)
    print("PRACTICE_TARGET " + msg)


def tr(loc, rot=(0.0, 0.0, 0.0)):
    t = U.Transform()
    t.translation = U.Vector(*loc)
    t.rotation = U.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2]).quaternion()
    t.scale3d = U.Vector(1.0, 1.0, 1.0)
    return t


def popt(mat_id):
    o = U.GeometryScriptPrimitiveOptions()
    o.material_id = mat_id
    o.polygroup_mode = U.GeometryScriptPrimitivePolygroupMode.PER_FACE
    # 贴图材质需要按尺寸等比展开的 UV：UNIFORM 保持纹素密度一致，木纹/漆面不拉伸。
    uv_mode = getattr(U, "GeometryScriptPrimitiveUVMode", None)
    if uv_mode is not None:
        o.uv_mode = uv_mode.UNIFORM
    return o


def append_cyl(mesh, loc, radius, height, mat, steps=48):
    # 圆柱默认 Z 轴、BASE 原点：pitch +90 把 +Z 转到 +X（朝靶面法线方向堆叠）。
    U.GeometryScript_Primitives.append_cylinder(
        mesh, popt(mat), tr(loc, (0.0, 90.0, 0.0)),
        radius=radius, height=height, radial_steps=steps, height_steps=0,
        capped=True, origin=U.GeometryScriptPrimitiveOriginMode.BASE)


def append_leg(mesh, base, tip, thick, mat):
    # 腿为局部 +Z 向顶点的长方体。UE Rotator 实测约定：正 roll 把 +Z 倒向 +Y，正 pitch 把 +Z 倒向 -X。
    dx, dy, dz = tip[0] - base[0], tip[1] - base[1], tip[2] - base[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    roll = math.degrees(math.atan2(dy, dz))
    pitch = -math.degrees(math.atan2(dx, dz))
    U.GeometryScript_Primitives.append_box(
        mesh, popt(mat), tr(base, (roll, pitch, 0.0)),
        dimension_x=2 * thick, dimension_y=2 * thick, dimension_z=length,
        origin=U.GeometryScriptPrimitiveOriginMode.BASE)


def append_box(mesh, center, dims, mat):
    U.GeometryScript_Primitives.append_box(
        mesh, popt(mat), tr(center),
        dimension_x=dims[0], dimension_y=dims[1], dimension_z=dims[2],
        origin=U.GeometryScriptPrimitiveOriginMode.CENTER)


def build():
    # 重跑幂等：删掉旧网格资产再建；材质槽绑 MAT_BINDINGS 里的现成游戏材质。
    if U.load_asset("%s/%s.%s" % (OUT, MESH_NAME, MESH_NAME)):
        U.EditorAssetLibrary.delete_asset("%s/%s.%s" % (OUT, MESH_NAME, MESH_NAME))
        say("deleted previous %s" % MESH_NAME)
    mesh = U.DynamicMesh()
    U.GeometryScript_Materials.enable_material_i_ds(mesh)

    # 靶面：背板 + 5 层递缩圆盘叠出同心环（前层凸出 1.2cm，真实分层靶读感）。
    append_cyl(mesh, (-BACKER_HALF, 0, FACE_Z), BACKER_R, 6.0, M_WOOD)
    step = BACKER_HALF
    for radius, mat in ((45.0, M_WHITE), (36.0, M_RED), (27.0, M_WHITE), (18.0, M_RED), (9.0, M_BULL)):
        append_cyl(mesh, (step, 0, FACE_Z), radius, 1.2, mat)
        step += 1.2
    # 中心木销穿背板入架。
    append_cyl(mesh, (-13.0, 0, FACE_Z), 2.2, 22.0, M_BULL, steps=24)

    # 木架：两前腿 Y 向张开 + 后腿成三脚，顶点并到背后卡块；横档 + 脚垫。
    append_leg(mesh, (-4.0, -52.0, 0.0), (-4.0, -3.0, 192.0), 5.0, M_WOOD)
    append_leg(mesh, (-4.0, 52.0, 0.0), (-4.0, 3.0, 192.0), 5.0, M_WOOD)
    append_leg(mesh, (-48.0, 0.0, 0.0), (-5.0, 0.0, 186.0), 5.0, M_WOOD)
    append_box(mesh, (-8.0, 0.0, 190.0), (9.0, 20.0, 16.0), M_WOOD)        # 顶部卡块（夹住背板后缘）
    append_box(mesh, (-3.9, 0.0, 62.0), (6.0, 74.0, 7.0), M_WOOD)          # 前腿横档
    append_box(mesh, (-4.0, -52.0, 2.5), (14.0, 22.0, 5.0), M_WOOD)        # 脚垫
    append_box(mesh, (-4.0, 52.0, 2.5), (14.0, 22.0, 5.0), M_WOOD)
    append_box(mesh, (-48.0, 0.0, 2.5), (18.0, 14.0, 5.0), M_WOOD)

    opts = U.GeometryScriptCreateNewStaticMeshAssetOptions()
    opts.enable_nanite = False
    opts.enable_recompute_normals = False
    opts.enable_recompute_tangents = False
    sm, outcome = U.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
        mesh, "%s/%s" % (OUT, MESH_NAME), opts)
    say("create outcome=%s asset=%s" % (outcome, sm.get_path_name() if sm else None))
    assert sm, "static mesh creation failed"

    # 低模道具（<2k tri）：复杂碰撞即渲染网格，命中精度直接等于环面真形。
    bs = sm.get_editor_property("body_setup")
    bs.set_editor_property("collision_trace_flag", U.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)

    mats = []
    for path in MAT_BINDINGS:
        m = U.load_asset(path + "." + path.rsplit("/", 1)[-1])
        assert m, "material not found: %s" % path
        mats.append(m)
    assert len(sm.static_materials) == len(mats), "slot count %d != %d" % (len(sm.static_materials), len(mats))
    for i, m in enumerate(mats):
        sm.set_material(i, m)
    U.EditorAssetLibrary.save_loaded_asset(sm)

    for name in LEGACY_MATS:
        legacy = "%s/%s.%s" % (OUT, name, name)
        if U.load_asset(legacy):
            U.EditorAssetLibrary.delete_asset(legacy)
            say("deleted legacy material %s" % name)

    receipt = {
        "asset": sm.get_path_name(),
        "slots": [{"index": i, "slot": str(s.material_slot_name),
                   "material": s.material_interface.get_path_name() if s.material_interface else None}
                  for i, s in enumerate(sm.static_materials)],
        "bounds": str(sm.get_bounds().box_extent),
        "triangles": int(U.EditorStaticMeshLibrary.get_number_sections(sm, 0).num()) if hasattr(U.EditorStaticMeshLibrary, "get_number_sections") else -1,
        "collision": "CTF_USE_COMPLEX_AS_SIMPLE",
    }
    with open(os.path.join(SRC, "mesh_receipt.json"), "w") as f:
        f.write(json.dumps(receipt, indent=2, default=str))
    say("saved " + sm.get_path_name())
    say("receipt " + json.dumps(receipt, default=str))


build()
