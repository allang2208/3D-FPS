"""只读探测（不写任何资产/关卡）：确认喷泉的**世界高度**与地面关系。

背景：`place_fountain_2x_20260918.py` 把 actor 摆到 z=−360（脚本想按"pivot 在包围盒中心"贴地），
但喷泉网格的 pivot 在**底面**（包围盒 origin_z=360），所以喷泉可能整座沉进地面 3.6 m——
这会同时解释"水看着像固体"（水盘都在地下/齐地面）与"喷水位置不对"（水柱相对可见塔尖偏高）。

编辑器开着也能跑（load_level 只读，不触发保存）。"""

import unreal

LEVEL = "/Game/GameMaps/DayNight_Lighting"


def log(m):
    print("[lvl] " + m)


les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not les or not les.load_level(LEVEL):
    log("load_level failed")
    raise SystemExit(0)
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_sub.get_all_level_actors()
log("actors=%d" % len(actors))

interesting = [a for a in actors if any(k in (a.get_actor_label() or "")
                                        for k in ("Floor", "Fountain", "Pavilion", "Platform", "Ground", "Terrain"))]
for a in interesting[:25]:
    o, e = a.get_actor_bounds(False)
    log("%-28s %-26s loc=(%.0f,%.0f,%.0f) z=[%.0f..%.0f]" % (
        a.get_actor_label() or a.get_name(), a.get_class().get_name(),
        a.get_actor_location().x, a.get_actor_location().y, a.get_actor_location().z,
        o.z - e.z, o.z + e.z))

# 喷泉本体：直接看它的网格组件世界包围盒（actor 变换 + 网格 pivot）
fountains = [a for a in actors if "ColdSteelFountain" in a.get_class().get_name()]
log("ColdSteelFountain count=%d" % len(fountains))
for f in fountains:
    loc = f.get_actor_location()
    comps = f.get_components_by_class(unreal.StaticMeshComponent)
    for c in comps:
        if not c.get_static_mesh():
            continue
        o, e = c.get_world_bounds() if hasattr(c, "get_world_bounds") else (None, None)
        log("  comp %-18s mesh=%-24s worldZ=[%.0f..%.0f] worldXY=(%.0f,%.0f)" % (
            c.get_name(), c.get_static_mesh().get_name(),
            (o.z - e.z) if o else -1, (o.z + e.z) if o else -1,
            loc.x, loc.y))
    # 向下打一条线：看地面在哪（无头/编辑器世界都试一次，失败就只报日志）
    try:
        start = unreal.Vector(loc.x, loc.y, loc.z + 3000.0)
        end = unreal.Vector(loc.x, loc.y, loc.z - 3000.0)
        hit = unreal.SystemLibrary.line_trace_single(
            f.get_world(), start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
            unreal.DrawDebugTrace.NONE, True)
        log("  trace down from %.0f -> block=%s hitZ=%.1f actor=%s" % (
            start.z, hit[0], hit[1].z if hit[0] else -9999.0,
            hit[3].get_actor().get_actor_label() if hit[0] and hit[3] else "None"))
    except Exception as exc:  # noqa: BLE001
        log("  trace failed: %s" % exc)
log("done")
