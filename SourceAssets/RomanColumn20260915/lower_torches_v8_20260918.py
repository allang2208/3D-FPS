"""把柱廊 6 支火把整体下移（跟罗马柱的衔接位置降低），只改这 6 个 actor 的 Z，不重新加载地图。

  python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/lower_torches_v8_20260918.py

- 直接作用于**当前打开**的世界，不调用 load_map，所以不会丢掉别的会话未保存的编辑。
- 前提：当前打开的关卡就是 DayNight_Lighting。PIE 运行中**可以**跑：改的是编辑器世界的 actor，
  跟别人的 PIE 副本互不影响（按 2026-09-18 多会话规则，只有 C++ 编译 / 同一资产导入保存才需要排队）。
- 幂等：按绝对高度设值（TORCH_Z），重复运行结果相同。
"""

import unreal

MAP = "/Game/GameMaps/DayNight_Lighting"
TORCH_Z = 190.0          # v7 之前是 210：横臂/柱衔接点下移 20 cm，杯口 252.6 -> 232.6


def log(m):
    print("[lower8] " + m)


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world_path = world.get_path_name()
log("editor world = %s" % world_path)
if not world_path.startswith(MAP + "."):
    raise RuntimeError("当前打开的不是 %s（是 %s）；先切到该地图再运行。" % (MAP, world_path))
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
    log("PIE 正在运行：本次改的是编辑器世界，不影响 PIE 副本，继续。")

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
moved = 0
for actor in sub.get_all_level_actors():
    label = actor.get_actor_label()
    if not label.startswith("ColonnadeTorch_"):
        continue
    loc = actor.get_actor_location()
    actor.set_actor_location(unreal.Vector(loc.x, loc.y, TORCH_Z), False, False)
    moved += 1
    log("  %-20s z %.0f -> %.0f" % (label, loc.z, TORCH_Z))

if moved != 6:
    raise RuntimeError("只找到 %d 个 ColonnadeTorch_*，预期 6 个；没有保存。" % moved)

saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("map save=%s moved=%d" % (saved, moved))
log("RESULT: " + ("PASS" if saved and moved == 6 else "CHECK"))
