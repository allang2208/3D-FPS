"""单扇门的门框与门板：进深 40 cm、宽 120 cm、高度 240 cm（2026-09-18 第二～四轮＋第五轮）。

用户口径：
  - 第二轮："统一门框的进深大小为 20 cm 体素格的整数倍，设置为 **40 CM**。"
  - 第三轮："同步调整高度，做好高度统一 **2.2 米**，门、门框都同步调整。"
  - 第四轮："高度调整为 **2.4 米**。"
  - 第五轮（2026-09-19，本轮）："门跟体素建造之间有缝隙，无法贴合" —— 根因正是第二轮刻意保留的
    宽度 113.99：占格 Y=6 格（120 cm）而门框只有 114 cm，两侧各差 3.005 cm，20 cm 体素填不进，
    门框与墙之间就透缝。本轮把宽度也统一成 **120 cm（6 格）**，三轴全部整格。

| 新资产 | 源（Door System 包） | 源尺寸（cm） | 目标（cm） | 缩放 |
| --- | --- | --- | --- | --- |
| `/Game/Props/SingleDoor20260918/SM_SingleDoorFrame_D40` | `SM_DoorFrame` | 24.84 × 113.99 × 212.00 | **40 × 120 × 240** | 进深 40/24.84 ＝ 2 格、宽 120/113.99 ＝ 6 格、高度 240/212 ＝ 12 格 |
| `/Game/Props/SingleDoor20260918/SM_SingleDoorLeaf_D40` | `SM_Door` | 18.48 × 90.00 × 200.00 | **18.48 × 94.75 × 226.42** | Y 随门框洞口同比例 120/113.99、Z 同比例 240/212；X 板厚不缩 |

- 包门框的洞口正好是 **90 × 200 ＝ 门板尺寸**（实测顶点：洞口 y ±45、z 0..200），所以门框与门板按**同一组比例**
  缩放后洞口仍被门板填满，门板／门框相对关系不变——"同高度、一起调"就是这个意思。宽度同理：
  洞口随外框从 90 → 90×120/113.99 ≈ 94.75，门板 Y 用同一比例跟着走。
- **X（板厚 18.48）不缩**：门板厚度是名义板厚，缩它会连带动铰链贴面与摆向（skill 第二轮结论 1）。
- 占格 = 包围盒/20 向上取整 → **(2,6,12)**（本轮三轴整除后与实际外形完全一致，不再虚占）；
  调色板 `door_*` 三条的 `Footprint` 由
  `SourceAssets/SingleDoor20260918/register_single_door_prefabs_20260918.py` 同步。
- **资产名不带高度**（`…_D40` 只标进深）：高度是按格子调的，再改一次只改本脚本的 `HEIGHT_CM` 重跑，
  C++ 路径与调色板脚本都不用动。

三条口径（缩放事故的教训，见 skills/asset-model-workflow 的"缩放已有网格"一节）：
  1. 不重建几何：`copy_mesh_from_static_mesh → scale_mesh(逐轴) → copy_mesh_to_static_mesh`；
  2. **逐槽拷回材质**：`copy_mesh_to_static_mesh` 默认只留一个空槽（曾把门扇的 M_Glass 小窗弄丢过），
     容器用 `duplicate_asset` 复制源资产（本版 Python 没有 `StaticMeshFactoryNew`）；
  3. 门框是**环状**网格：清空过期简单碰撞并设 `CTF_USE_COMPLEX_AS_SIMPLE`（包成盒会把门洞堵死）；
     门板是实体薄板，用 AlignedBoxes。

包里的 `/Game/DoorSystem/**` 原样不动（物理门 `door_physics` 还在用）。
**保存要核实真落盘**：并行会话的 Unreal 进程占着包时保存会静默失败（`Error saving`／`Error Code 32`），
脚本里的读回只是同进程内存值——跑之前确认没有其它 UnrealEditor 在跑，跑完核对 `.uasset` 的 mtime。

运行（编辑器关闭时最稳）：
  UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
      -Script=D:/FPS3D/FPSGAME/SourceAssets/SingleDoor20260918/bake_single_door_meshes_20260918.py \
      -unattended -nop4 -nosplash -NullRHI -nosound -abslog=<日志>
"""

import time

import unreal

PACK_FRAME = "/Game/DoorSystem/Demo/StarterContent/Props/SM_DoorFrame"
PACK_LEAF = "/Game/DoorSystem/Demo/StarterContent/Props/SM_Door"
DIR = "/Game/Props/SingleDoor20260918"
DEPTH_CM = 40.0      # 进深：2 格体素（用户指定）
WIDTH_CM = 120.0     # 外廓宽度：6 格体素（2026-09-19 第五轮：消除门框与墙之间各 3 cm 的透缝）
HEIGHT_CM = 240.0    # 外廓高度：12 格体素（2.4 m，用户指定）
LOG = []


def log(m):
    print("[door-h240] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-28s %s" % (label, "OK" if ok else "FAIL"))


def load_dynamic(path):
    mesh = unreal.EditorAssetLibrary.load_asset(path) or unreal.load_asset(path)
    if not mesh:
        return None, None
    dm = unreal.DynamicMesh()
    dm, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    if dm is None or "fail" in str(outcome).lower():
        return mesh, None
    return mesh, dm


def copy_material_slots(source, target):
    rebuilt = []
    for slot in list(source.get_editor_property("static_materials") or []):
        entry = unreal.StaticMaterial()
        try:
            entry.set_editor_property("material_interface", slot.get_editor_property("material_interface"))
            entry.set_editor_property("material_slot_name", slot.get_editor_property("material_slot_name"))
        except Exception as exc:  # noqa: BLE001
            log("材质槽拷贝失败：%s" % exc)
        rebuilt.append(entry)
    if not rebuilt:
        rebuilt = [unreal.StaticMaterial()]
    target.set_editor_property("static_materials", rebuilt)
    return len(rebuilt)


def clear_simple_collision(target):
    setup = target.get_editor_property("body_setup")
    if not setup:
        return
    for prop in ("agg_geom", "aggregate_geometry"):
        try:
            agg = setup.get_editor_property(prop)
        except Exception:  # noqa: BLE001
            continue
        if not agg:
            continue
        for elem in ("box_elems", "convex_elems", "sphere_elems", "sphyl_elems", "taper_elems"):
            try:
                agg.set_editor_property(elem, [])
            except Exception:  # noqa: BLE001
                pass
        break
    setup.set_editor_property("collision_trace_flag",
                              unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)


def bake(label, source_path, target_path, target_size, ring):
    """逐轴缩放到 target_size；ring=True 用三角面碰撞（门框），否则 AlignedBoxes（门板）。"""
    source, dm = load_dynamic(source_path)
    check("load_" + label, dm is not None)
    if not dm:
        return None
    bb = source.get_bounds()
    native = (bb.box_extent.x * 2.0, bb.box_extent.y * 2.0, bb.box_extent.z * 2.0)
    scale = (target_size[0] / native[0], target_size[1] / native[1], target_size[2] / native[2])
    log("%-22s 源 %.2f × %.2f × %.2f → 目标 %.2f × %.2f × %.2f 缩放 %.4f/%.4f/%.4f" % (
        label, native[0], native[1], native[2], target_size[0], target_size[1], target_size[2],
        scale[0], scale[1], scale[2]))
    dm = unreal.GeometryScript_MeshTransforms.scale_mesh(
        dm, unreal.Vector(scale[0], scale[1], scale[2]), unreal.Vector(0.0, 0.0, 0.0), True)

    target = unreal.EditorAssetLibrary.load_asset(target_path) or unreal.load_asset(target_path)
    if not target:
        # 先复制一份包资产当容器（材质槽一并带过来），再覆盖几何。
        unreal.EditorAssetLibrary.make_directory(target_path.rsplit("/", 1)[0])
        unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
        target = unreal.EditorAssetLibrary.load_asset(target_path) or unreal.load_asset(target_path)
    check("target_asset_" + label, target is not None)
    if not target:
        return None
    _, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
        dm, target, unreal.GeometryScriptCopyMeshToAssetOptions(),
        unreal.GeometryScriptMeshWriteLOD(), True)
    check("copy_to_static_" + label, "fail" not in str(outcome).lower())
    log("  copy_to_static outcome=%s" % outcome)
    slots = copy_material_slots(source, target)
    log("  材质槽：源 %d → 目标 %d" % (
        len(source.get_editor_property("static_materials") or []), slots))
    unreal.EditorAssetLibrary.save_loaded_asset(target, True)
    time.sleep(1.0)
    if ring:
        clear_simple_collision(target)          # 环状网格：三角面即碰撞体，洞口才不被堵死
    else:
        unreal.ModelingService.generate_collision(target_path, "AlignedBoxes", 1, 25, True)
    unreal.EditorAssetLibrary.save_loaded_asset(target, True)

    back = unreal.EditorAssetLibrary.load_asset(target_path) or unreal.load_asset(target_path)
    bb2 = back.get_bounds()
    got = (round(bb2.box_extent.x * 2, 2), round(bb2.box_extent.y * 2, 2), round(bb2.box_extent.z * 2, 2))
    body = back.get_editor_property("body_setup")
    geom = body.get_editor_property("agg_geom") if body else None
    log("  读回 %s bbox %.2f × %.2f × %.2f origin=(%.2f, %.2f, %.2f) tris=%d slots=%d box=%d convex=%d" % (
        target_path.rsplit("/", 1)[-1], got[0], got[1], got[2],
        bb2.origin.x, bb2.origin.y, bb2.origin.z, back.get_num_triangles(0),
        len(back.get_editor_property("static_materials") or []),
        len(geom.get_editor_property("box_elems")) if geom else -1,
        len(geom.get_editor_property("convex_elems")) if geom else -1))
    check("size_" + label, all(abs(got[i] - target_size[i]) < 0.3 for i in range(3)))
    check("slots_" + label,
          len(back.get_editor_property("static_materials") or []) ==
          len(source.get_editor_property("static_materials") or []))
    return got, native


# 门框：进深 40（2 格）＋宽 120（6 格）＋高度 240（12 格），三轴全部整格（2026-09-19 第五轮）
pack_frame, _ = load_dynamic(PACK_FRAME)
native_frame = (pack_frame.get_bounds().box_extent.x * 2.0,
                pack_frame.get_bounds().box_extent.y * 2.0,
                pack_frame.get_bounds().box_extent.z * 2.0)
frame_target = (DEPTH_CM, WIDTH_CM, HEIGHT_CM)
bake("frame", PACK_FRAME, DIR + "/SM_SingleDoorFrame_D40", frame_target, True)

# 门板：Y／Z 与门框同一组比例（洞口 90×200 ＝ 门板尺寸，同比例缩放后缩完仍然严丝合缝）；X 板厚不缩
leaf_scale_y = WIDTH_CM / native_frame[1]
leaf_scale_z = HEIGHT_CM / native_frame[2]
pack_leaf, _ = load_dynamic(PACK_LEAF)
native_leaf = (pack_leaf.get_bounds().box_extent.x * 2.0,
               pack_leaf.get_bounds().box_extent.y * 2.0,
               pack_leaf.get_bounds().box_extent.z * 2.0)
leaf_target = (round(native_leaf[0], 2), round(native_leaf[1] * leaf_scale_y, 2),
               round(native_leaf[2] * leaf_scale_z, 2))
bake("leaf", PACK_LEAF, DIR + "/SM_SingleDoorLeaf_D40", leaf_target, False)

log("门框 %.2f × %.2f × %.2f（应 ＝ 40 × 120 × 240）：占格按 %s" % (
    frame_target[0], frame_target[1], frame_target[2],
    tuple(max(1, int((v + 19.9) // 20)) for v in frame_target)))
log("门板 %.2f × %.2f × %.2f（洞口 90 × 200 同比例 → %.2f × %.2f），Y 比例 %.6f，Z 比例 %.6f" % (
    leaf_target[0], leaf_target[1], leaf_target[2],
    native_leaf[1] * leaf_scale_y, native_leaf[2] * leaf_scale_z, leaf_scale_y, leaf_scale_z))
check("frame_footprint_2_6_12", tuple(max(1, int((v + 19.9) // 20)) for v in frame_target) == (2, 6, 12))
check("frame_width_on_grid", abs(frame_target[1] - 120.0) < 0.05)
check("leaf_fits_frame_opening", abs(leaf_target[1] - native_leaf[1] * leaf_scale_y) < 0.05
      and abs(leaf_target[2] - native_leaf[2] * leaf_scale_z) < 0.05
      and leaf_target[1] < frame_target[1] and leaf_target[2] < frame_target[2])
check("pack_untouched", abs(native_frame[1] - 113.99) < 0.05 and abs(native_frame[2] - 212.0) < 0.05)

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
