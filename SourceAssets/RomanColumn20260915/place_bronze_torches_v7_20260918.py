"""把柱廊上的 6 支火把从 StaticMeshActor 换成 ABronzeTorch（网格 + 火焰 + 暖光 + 黄昏/夜晚自动点火）。

前置：`Source/FPSGAME/Building/BronzeTorch.h/.cpp` 必须已经**关闭编辑器全量编译**过
（Live Coding 不支持新增 UCLASS），脚本会先确认 `/Script/FPSGAME.BronzeTorch` 能加载。

运行（编辑器开着也行——按 2026-09-18 多会话规则，只按资产/关卡划归属，不覆盖他人改动）：
  python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/place_bronze_torches_v7_20260918.py

只作用于**当前打开**的世界并校验它就是 DayNight_Lighting，**不调用 load_map**（不会丢掉别人未保存的编辑）。

幂等：重复运行会先删掉上一轮的 ColonnadeTorch_* 与 ABronzeTorch，再按同一组柱轴心重建。
"""

import unreal

MAP = "/Game/GameMaps/DayNight_Lighting"
TORCH_CLASS_PATH = "/Script/FPSGAME.BronzeTorch"
D = "/Game/Props/RomanColumn20260915"
MESH = D + "/SM_BronzeTorch"
MATERIAL = D + "/M_Bronze"
# 火焰母版：Epic Niagara Examples（工程内既有授权依赖）。留空则只用点光。
FLAME = "/Game/NiagaraExamples/FX_Misc/NS_Fire"
FLAME_SCALE = 0.35

# 柱廊 C01..C06 柱轴心；local +X 托臂经 yaw=-90 指向世界 -Y（展示面）。
# z 用 190（不是旧的 210）：按用户要求把跟罗马柱的衔接位置下移 20 cm，杯口 252.6 -> 232.6。
COLUMNS = [(600.0 + 300.0 * k, 600.0, 190.0) for k in range(6)]
YAW = -90.0


def log(m):
    print("[place7] " + m)


def set_prop(obj, snake, pascal, value):
    """Live Coding 新注册的类只认 C++ 原名（PascalCase）；老类通常两者都认。两个都试。"""
    for name in (snake, pascal):
        try:
            obj.set_editor_property(name, value)
            return True
        except Exception:  # noqa: BLE001
            continue
    log("WARN 属性没写进去: %s / %s" % (snake, pascal))
    return False


torch_class = unreal.load_class(None, TORCH_CLASS_PATH)
if torch_class is None:
    raise RuntimeError(
        "找不到 %s：先关编辑器做一次全量编译（Live Coding 不能新增 UCLASS），再运行本脚本。" % TORCH_CLASS_PATH)

mesh = unreal.EditorAssetLibrary.load_asset(MESH)
material = unreal.EditorAssetLibrary.load_asset(MATERIAL)
flame = unreal.EditorAssetLibrary.load_asset(FLAME) if FLAME else None
if not mesh or not material:
    raise RuntimeError("torch mesh/material missing: %s / %s" % (MESH, MATERIAL))
log("assets: mesh=%s material=%s flame=%s" % (bool(mesh), bool(material), bool(flame)))

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world_path = world.get_path_name()
log("editor world = %s" % world_path)
if not world_path.startswith(MAP + "."):
    raise RuntimeError("当前打开的不是 %s（是 %s）；先切到该地图再运行。" % (MAP, world_path))
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError("PIE 正在运行：先停 PIE 再换火把（PIE 不能换 actor 类）。")
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# 先把上一轮的火把收干净（旧 StaticMeshActor 版 + 本类版），并按标签留一份位姿。
kept = {}
removed = 0
for actor in list(sub.get_all_level_actors()):
    label = actor.get_actor_label()
    if label.startswith("ColonnadeTorch_"):
        kept[label] = (actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d())
        sub.destroy_actor(actor)
        removed += 1
    elif actor.get_class().get_name() == "BronzeTorch":
        sub.destroy_actor(actor)
        removed += 1
log("removed %d previous torch actor(s), captured %d transform(s)" % (removed, len(kept)))

placed = []
for k in range(6):
    label = "ColonnadeTorch_%02d" % (k + 1)
    x, y, z = COLUMNS[k]
    location = unreal.Vector(x, y, z)
    rotation = unreal.Rotator(0.0, 0.0, YAW)
    scale = unreal.Vector(1.0, 1.0, 1.0)
    if label in kept:
        # 位置以 COLUMNS 为准（含 v8 下移后的高度）；旧 actor 只用来继承朝向与缩放。
        _, rotation, scale = kept[label]
    actor = sub.spawn_actor_from_class(torch_class, location, rotation)
    actor.set_actor_label(label)
    actor.set_actor_scale3d(scale)

    # 写 CDO 属性（保存进关卡，之后在编辑器里可见可改），并直接配一遍组件，避免依赖构造脚本重跑。
    set_prop(actor, "body_mesh", "BodyMesh", mesh)
    set_prop(actor, "body_material", "BodyMaterial", material)
    if flame:
        set_prop(actor, "flame_system", "FlameSystem", flame)
    set_prop(actor, "flame_scale", "FlameScale", FLAME_SCALE)
    # 与天空相位对齐的点火窗口（写进关卡实例，避免依赖补丁会话里的旧 CDO 默认值）。
    set_prop(actor, "ignite_hour", "IgniteHour", 16.5)
    set_prop(actor, "extinguish_hour", "ExtinguishHour", 6.0)
    body = actor.get_component_by_class(unreal.StaticMeshComponent)
    if body:
        body.set_static_mesh(mesh)
        body.set_material(0, material)
        body.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    flame_comp = actor.get_component_by_class(unreal.NiagaraComponent)
    if flame_comp and flame:
        flame_comp.set_asset(flame)
        flame_comp.set_relative_location(unreal.Vector(50.0, 0.0, 16.0), False, False)
    light_comp = actor.get_component_by_class(unreal.PointLightComponent)
    if light_comp:
        light_comp.set_relative_location(unreal.Vector(50.0, 0.0, 52.0), False, False)
    placed.append((label, actor.get_actor_location(), actor.get_class().get_name()))

for label, loc, cls in placed:
    log("  %-20s %-14s (%.0f,%.0f,%.0f)" % (label, cls, loc.x, loc.y, loc.z))

saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("map save=%s placed=%d" % (saved, len(placed)))
log("RESULT: " + ("PASS" if saved and len(placed) == 6 else "CHECK"))
