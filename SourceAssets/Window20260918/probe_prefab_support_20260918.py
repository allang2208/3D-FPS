"""诊断：构件（窗）在支撑被拆后会不会脱落，定位浮空成因。

在编辑器世界里临时生成一个隔离的调试建筑世界（独立 world key，脚本结束即销毁），
按"空地选址 → 空中孤立件 → 墙内开窗 → 拆支撑"分组打印方块数、构件数与窗 Actor 数。

    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/Window20260918/probe_prefab_support_20260918.py
"""

import hashlib
import os

import unreal

KEY = "ToolProbePrefabSupport20260918|DayNight_Lighting"
WALL_Y = 7           # 墙：1 格厚 × 7 格宽 × 11 格高
WALL_Z = 11
HOLE_Y = 5           # 窗占格 (1,5,5)
HOLE_Z = 5
HOLE_ROW = 4         # 窗洞底部离墙底 4 格 = 80 cm，保证窗底远离地面探测带
CANDIDATES = [(-30, -40), (10, -40), (-60, -20), (40, 20), (0, -10), (-100, -90), (60, -120)]


def editor_world():
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    return subsystem.get_game_world() or subsystem.get_editor_world()


def spawn_build_world():
    try:
        spawn = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class
    except Exception:  # noqa: BLE001
        spawn = unreal.EditorLevelLibrary.spawn_actor_from_class
    return spawn(unreal.VoxelBuildWorld, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0))


def terrain_z(world, cell_x, cell_y):
    start = unreal.Vector(cell_x * 20.0 + 10.0, cell_y * 20.0 + 10.0, 800.0)
    end = unreal.Vector(start.x, start.y, -800.0)
    hit = unreal.SystemLibrary.line_trace_single(
        world, start, end, unreal.TraceTypeQuery.ECC_VISIBILITY, True, [],
        unreal.DrawDebugTrace.NONE, True)
    if not isinstance(hit, unreal.HitResult):
        return None
    try:
        if hit.get_editor_property("actor") is None:
            return None
        return hit.get_editor_property("location").z
    except Exception:  # noqa: BLE001
        return None


def vec(cell):
    return unreal.IntVector(cell[0], cell[1], cell[2])


def wall_cells(base_x, base_y, base_z):
    return [vec((base_x, base_y + dy, base_z + dz)) for dy in range(WALL_Y) for dz in range(WALL_Z)]


def hole_cells(base_x, base_y, base_z):
    return [vec((base_x, base_y + 1 + dy, base_z + HOLE_ROW + dz)) for dy in range(HOLE_Y) for dz in range(HOLE_Z)]


def frame_cells(base_x, base_y, base_z):
    # 两列边墙 + 墙顶一行 + 窗洞正上方那一行：合起来把窗四周的体素清空。
    return ([vec((base_x, base_y, base_z + dz)) for dz in range(WALL_Z)]
            + [vec((base_x, base_y + WALL_Y - 1, base_z + dz)) for dz in range(WALL_Z)]
            + [vec((base_x, base_y + 1 + dy, base_z + WALL_Z - 1)) for dy in range(HOLE_Y)]
            + [vec((base_x, base_y + 1 + dy, base_z + HOLE_ROW + HOLE_Z)) for dy in range(HOLE_Y)])


def under_window_cells(base_x, base_y, base_z):
    """窗正下方到墙底的所有列（整根支撑柱）。"""
    return [vec((base_x, base_y + 1 + dy, base_z + dz)) for dy in range(HOLE_Y) for dz in range(HOLE_ROW)]


def report(build_world, world, label):
    windows = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ColdSteelWindow)
    print("  [%-30s] blocks=%-4s prefabs=%s windows=%s"
          % (label, build_world.block_count(), build_world.prefab_count(), len(windows)))


def report_falling(world, label):
    """占位 Actor 还在 + 网格在模拟物理 = 正在落体。"""
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.VoxelBuildPrefabActor):
        simulated = any(mesh.is_simulating_physics()
                        for mesh in actor.get_components_by_class(unreal.StaticMeshComponent))
        attached = actor.get_attached_actors()
        print("  [%s] placeholder=%s loc=%s simulating=%s attached=%s"
              % (label, actor.get_name(), actor.get_actor_location(), simulated,
                 [a.get_name() for a in attached]))


def pick_site(world, build_world):
    for cell_x, cell_y in CANDIDATES:
        surface = terrain_z(world, cell_x, cell_y)
        base_z = 0 if surface is None else int(round(surface / 20.0))
        accepted = build_world.edit_cells(wall_cells(cell_x, cell_y, base_z), unreal.Name("marble"))
        print("site (%d,%d): terrain_z=%s base_z=%d wall accepted=%s"
              % (cell_x, cell_y, surface, base_z, accepted))
        if accepted:
            return cell_x, cell_y, base_z
    return None


def main():
    world = editor_world()
    print("world: %s" % (world.get_name() if world else "None"))
    if not world:
        return
    build_world = spawn_build_world()
    if not build_world:
        print("spawn AVoxelBuildWorld failed")
        return
    try:
        print("debug_initialize(%s) -> %s" % (KEY, build_world.debug_initialize(KEY)))
        site = pick_site(world, build_world)
        if not site:
            print("no usable site found")
            return
        base_x, base_y, base_z = site
        print("chosen site: cells (%d,%d,%d)" % (base_x, base_y, base_z))

        # 对照 A：空中孤立的窗（四周无体素、无其他构件）
        isolated = vec((base_x + 20, base_y, base_z + 6))
        print("A. place an isolated airborne window at %s -> %s"
              % (isolated, build_world.place_prefab(unreal.Name("window_marble"), isolated, 0)))
        report(build_world, world, "after the isolated window")

        print("clear the wall from the site probe: %s"
              % build_world.edit_cells(wall_cells(base_x, base_y, base_z), unreal.Name("None")))

        # B. 重建墙 + 开窗洞 → 装窗
        print("B. rebuild the wall: %s" % build_world.edit_cells(wall_cells(base_x, base_y, base_z), unreal.Name("marble")))
        print("   cut the window hole: %s" % build_world.edit_cells(hole_cells(base_x, base_y, base_z), unreal.Name("None")))
        anchor = vec((base_x, base_y + 1, base_z + HOLE_ROW))
        print("   place the window at %s -> %s"
              % (anchor, build_world.place_prefab(unreal.Name("window_marble"), anchor, 0)))
        report(build_world, world, "after the window in the wall")

        # C. 拆掉窗正下方的整根支撑柱
        below = under_window_cells(base_x, base_y, base_z)
        print("C. remove the %d cells below the window: %s" % (len(below), build_world.edit_cells(below, unreal.Name("None"))))
        report(build_world, world, "after removing the row below")

        # D. 拆掉整圈墙（窗四面全空）
        print("D. remove the whole frame: %s" % build_world.edit_cells(frame_cells(base_x, base_y, base_z), unreal.Name("None")))
        report(build_world, world, "after removing the whole frame")
        report_falling(world, "fall state after D")

        # E. 再叠一件窗（相邻面应判为有支撑 —— 用来确认占格索引本身是活的）
        neighbour = vec((base_x, base_y + 1, base_z + HOLE_ROW + HOLE_Z))
        print("E. stack a second window on the leftover one at %s -> %s"
              % (neighbour, build_world.place_prefab(unreal.Name("window_marble"), neighbour, 0)))
        report(build_world, world, "after stacking a second window")

        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ColdSteelWindow):
            parent = actor.get_attach_parent_actor()
            print("  leftover window %s loc=%s parent=%s"
                  % (actor.get_name(), actor.get_actor_location(), parent.get_name() if parent else "None"))
        probe_save = "Voxel20_%s.sav" % hashlib.md5(KEY.encode()).hexdigest().upper()
        print("probe save file (可删): Saved/SaveGames/%s exists=%s"
              % (probe_save, os.path.exists(os.path.join("D:/FPS3D/FPSGAME/Saved/SaveGames", probe_save))))

        # 清场：本脚本在编辑器世界里放下的构件与占位 Actor 全部销毁（含上一轮遗留的同名件）。
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ColdSteelWindow):
            parent = actor.get_attach_parent_actor()
            actor.destroy_actor()
            if parent:
                parent.destroy_actor()
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.VoxelBuildPrefabActor):
            actor.destroy_actor()
        print("cleanup: windows=%d prefab actors=%d left"
              % (len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ColdSteelWindow)),
                 len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.VoxelBuildPrefabActor))))
    finally:
        print("destroy probe build world: %s" % build_world.destroy_actor())


main()
