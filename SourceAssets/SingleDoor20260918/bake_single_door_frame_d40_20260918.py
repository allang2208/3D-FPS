"""单扇门的门框：把包里 SM_DoorFrame 的**进深**缩放到 40 cm（其余两轴不动），供 AColdSteelDoor 使用。

用户口径（2026-09-18 第二轮）："统一门框的进深大小为 20 cm 体素格的整数倍，设置为 40 CM。"
  - 源：`/Game/DoorSystem/Demo/StarterContent/Props/SM_DoorFrame`，原生 24.8 × 114 × 212 cm（进深 24.8＝非整格）；
  - 目标：`/Game/Props/SingleDoor20260918/SM_SingleDoorFrame_D40`，**40 × 114 × 212**（进深 40 ＝ 2 格体素）；
  - 门扇不动（仍是包里的 `SM_Door`，见 `ColdSteelDoor.cpp` 的默认网格）：Actor 一律按包围盒摆位，
    门框只是变深，门板位置、铰链、开合角、占格 (2,6,11) 全都不变。

三条口径（上一轮缩放事故的教训，见 skills/asset-model-workflow 的"缩放已有网格"一节）：
  1. 不重建几何：`copy_mesh_from_static_mesh → scale_mesh(逐轴) → copy_mesh_to_static_mesh`；
  2. **逐槽拷回材质**：`copy_mesh_to_static_mesh` 默认只留一个空槽（上一轮把门扇的 M_Glass 小窗弄丢了）；
  3. 门框是**环状**网格：清空过期简单碰撞，改 `CTF_USE_COMPLEX_AS_SIMPLE`（三角面即碰撞体），
     包成盒会把门洞整个堵死。

包里的 `/Game/DoorSystem/**` 原样不动（物理门 `door_physics` 还在用）。

运行（编辑器关闭时最稳）：
  UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
      -Script=D:/FPS3D/FPSGAME/SourceAssets/SingleDoor20260918/bake_single_door_frame_d40_20260918.py \
      -unattended -nop4 -nosplash -NullRHI -nosound -abslog=<日志>
"""

import time

import unreal

PACK_FRAME = "/Game/DoorSystem/Demo/StarterContent/Props/SM_DoorFrame"
PACK_LEAF = "/Game/DoorSystem/Demo/StarterContent/Props/SM_Door"
TARGET = "/Game/Props/SingleDoor20260918/SM_SingleDoorFrame_D40"
DEPTH_CM = 40.0
LOG = []


def log(m):
    print("[doorframe40] " + m)


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


source, dm = load_dynamic(PACK_FRAME)
leaf_source, _ = load_dynamic(PACK_LEAF)
check("pack_frame_loadable", dm is not None)
if dm:
    bb = source.get_bounds()
    native = (bb.box_extent.x * 2.0, bb.box_extent.y * 2.0, bb.box_extent.z * 2.0)
    scale = (DEPTH_CM / native[0], 1.0, 1.0)
    log("SM_DoorFrame 源 %.2f × %.2f × %.2f → 目标 %.2f × %.2f × %.2f 缩放 %.4f/%.4f/%.4f" % (
        native[0], native[1], native[2], DEPTH_CM, native[1], native[2], scale[0], scale[1], scale[2]))
    dm = unreal.GeometryScript_MeshTransforms.scale_mesh(
        dm, unreal.Vector(scale[0], scale[1], scale[2]), unreal.Vector(0.0, 0.0, 0.0), True)

    target = unreal.EditorAssetLibrary.load_asset(TARGET) or unreal.load_asset(TARGET)
    if not target:
        # 先复制一份包资产当容器（材质槽一并带过来），再覆盖几何；
        # 不用 create_asset：本版 Python 里没有 unreal.StaticMeshFactoryNew。
        unreal.EditorAssetLibrary.make_directory(TARGET.rsplit("/", 1)[0])
        unreal.EditorAssetLibrary.duplicate_asset(PACK_FRAME, TARGET)
        target = unreal.EditorAssetLibrary.load_asset(TARGET) or unreal.load_asset(TARGET)
    check("target_asset", target is not None)
    if target:
        _, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
            dm, target, unreal.GeometryScriptCopyMeshToAssetOptions(),
            unreal.GeometryScriptMeshWriteLOD(), True)
        check("copy_to_static", "fail" not in str(outcome).lower())
        log("copy_to_static outcome=%s" % outcome)
        slots = copy_material_slots(source, target)
        log("材质槽：源 %d → 目标 %d" % (
            len(source.get_editor_property("static_materials") or []), slots))
        unreal.EditorAssetLibrary.save_loaded_asset(target, True)
        time.sleep(1.0)
        # 环状网格：清掉过期简单碰撞，用三角面当碰撞体（包成盒会堵死门洞）。
        setup = target.get_editor_property("body_setup")
        if setup:
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
            check("collision_complex_as_simple", True)
        unreal.EditorAssetLibrary.save_loaded_asset(target, True)

        back = unreal.EditorAssetLibrary.load_asset(TARGET) or unreal.load_asset(TARGET)
        bb2 = back.get_bounds()
        got = (round(bb2.box_extent.x * 2, 2), round(bb2.box_extent.y * 2, 2), round(bb2.box_extent.z * 2, 2))
        log("读回 %s bbox %.2f × %.2f × %.2f origin=(%.2f, %.2f, %.2f) tris=%d slots=%d" % (
            "SM_SingleDoorFrame_D40", got[0], got[1], got[2],
            bb2.origin.x, bb2.origin.y, bb2.origin.z, back.get_num_triangles(0),
            len(back.get_editor_property("static_materials") or [])))
        body = back.get_editor_property("body_setup")
        geom = body.get_editor_property("agg_geom") if body else None
        log("简单碰撞：box=%d convex=%d（应为 0／0，洞口靠三角面碰撞保持通行）" % (
            len(geom.get_editor_property("box_elems")) if geom else -1,
            len(geom.get_editor_property("convex_elems")) if geom else -1))
        check("bbox_depth_40", abs(got[0] - DEPTH_CM) < 0.2)
        check("bbox_other_axes_unchanged",
              abs(got[1] - native[1]) < 0.2 and abs(got[2] - native[2]) < 0.2)
        check("slots_kept",
              len(back.get_editor_property("static_materials") or []) ==
              len(source.get_editor_property("static_materials") or []))
        # 占格仍按 40 × 114 × 212 向上取整 → (2,6,11)，与调色板 door_* 条目一致。
        cells = tuple(max(1, int((v + 19.9) // 20)) for v in got)
        log("占格 %s（调色板 door_* 条目应为 (2,6,11)）" % (cells,))
        check("footprint_unchanged", cells == (2, 6, 11))

# 包资产原样（物理门还在用）
if leaf_source:
    bbl = leaf_source.get_bounds()
    log("包门扇原样：SM_Door = %.2f × %.2f × %.2f（未改动）" % (
        bbl.box_extent.x * 2, bbl.box_extent.y * 2, bbl.box_extent.z * 2))

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
