"""200×200 双开门网格：门框 SM_DoubleDoorFrame_200 + 单扇门扇 SM_DoubleDoorLeaf_200（左右两扇共用）。

尺寸口径（cm，20 cm 体素格；2026-09-18 用户指定 2×2 m 双开门，当天第三／四轮把高度统一到 2.4 m）：
  门框 **40(X)** × 200(Y) × **240(Z)** —— 与单扇门统一进深 40（2 格体素）与高度 240（12 格体素），
  占格 **(2,10,12)**；洞口 184 × **224**（边梃 8），两组门扇各 91.5 × **223** 对开，中间留 1 cm 缝、上下各留 0.5 cm。
  门扇高度不写死：`LEAF_H = FRAME_H − 2×边梃 − 1 cm 缝`，以后改高度只动 `FRAME_H` 一处。

门扇**不再是自建盒体**（2026-09-18 用户第二轮口径："把现在单开门的单门模型放到双开门中，单扇门进行替换"）：
直接拿包里单扇门用的 `SM_Door` 逐轴缩放到一扇洞口（见 `bake_pack_leaf()`），
  - 逐轴比例 = (1.0, 91.5/90, LEAF_H/200)：X 不缩放，门扇板厚保持 5 cm ＝ `LeafHalfThicknessCm×2`，铰链深度才对得上；
  - 绕 Z 转 180° 把把手转到网格 **+Y**（包门扇把手在网格 −Y），与 `AColdSteelWindow`／`AColdSteelDoubleDoor`
    "把手 +Y、右扇转 180°"的约定一致，C++ 一行都不用改；
  - 平移把包围盒中心放回网格原点（原模型 pivot 在角落、包围盒中心偏 (0,−45,+100)），
    否则右扇那 180° 会把门扇整体偏出半个门宽（`AlignGeometry` 的 Y 公式只对"包围盒中心＝原点"成立）。

门框仍用 `append_box` 拼**闭合盒体**（不做布尔），碰撞 AlignedBoxes——凸包会把 184×184 的洞口整个堵死。
门扇缩放后要**逐槽拷回材质**（`copy_mesh_to_static_mesh` 默认只留一个空槽，包门扇的 M_Glass 小窗会丢，
2026-09-18 上一轮就是栽在这里）。

运行（编辑器必须关闭）：
  UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
      -Script=D:/FPS3D/FPSGAME/SourceAssets/DoubleDoor20260918/build_double_door_meshes_20260918.py \
      -unattended -nop4 -nosplash -NullRHI -nosound -abslog=<日志>
"""

import json
import os
import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/DoubleDoor20260918"
FRAME_PATH = DIR + "/SM_DoubleDoorFrame_200"
LEAF_PATH = DIR + "/SM_DoubleDoorLeaf_200"
MATERIAL = "/Game/Building/Voxels/Rounded/M_Voxel_Wood"
OUT_DIR = r"D:\FPS3D\FPSGAME\SourceAssets\DoubleDoor20260918\preview_20260918"
COLOR_JSON = os.path.join(OUT_DIR, "material_colors.json")

# --- 尺寸（cm）。改这里就要同步调色板占格与 ColdSteelDoubleDoor 的 FrameMemberCm／LeafHalfThicknessCm。
FRAME_DEPTH, FRAME_W, FRAME_H = 40.0, 200.0, 240.0   # 进深 40 = 2 格、高 240 = 12 格（与单扇门统一，用户指定）
MEMBER = 8.0                      # 门框边梃宽
LEAF_W = 91.5                     # 一扇的宽度：洞口 184 的一半，中间留 1 cm 缝
LEAF_H = FRAME_H - 2.0 * MEMBER - 1.0   # 223：洞口 224 高，上下各留 0.5 cm 缝
LEAF_NOMINAL_T = 5.0              # 门扇板厚 ＝ ColdSteelDoubleDoor 的 2×LeafHalfThicknessCm
PACK_LEAF = "/Game/DoorSystem/Demo/StarterContent/Props/SM_Door"   # 单扇门用的门扇模型（本轮的替换来源）

STARTED = time.time()
LOG = []


def log(m):
    print("[door2] " + m)


def tf(x=0.0, y=0.0, z=0.0, pitch=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    # Python 的 Rotator 构造是 (roll, pitch, yaw)；pitch=+90 把圆柱的 +Z 轴转成 -X，用来做横倒的杆。
    t.rotation = unreal.Rotator(0.0, pitch, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def box(handle, label, centre, size):
    result = SV.append_box(handle, tf(*centre), size[0], size[1], size[2], 0, 0, 0, "Center", 0)
    ok = getattr(result, "success", None)
    LOG.append((label, ok, getattr(result, "message", "")))
    log("%-16s centre=(%.1f, %.1f, %.1f) size=(%.1f, %.1f, %.1f) %s" % (
        label, centre[0], centre[1], centre[2], size[0], size[1], size[2], ok))
    return result


def load_dynamic(path):
    """读成 DynamicMesh：GeometryScript 原生路线（copy_mesh_from_static_mesh）。"""
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
    """把源资产的材质槽逐槽拷回目标（copy_mesh_to_static_mesh 默认只留一个空槽）。"""
    slots = list(source.get_editor_property("static_materials") or [])
    rebuilt = []
    for slot in slots:
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


def ensure_asset(source_path, target_path):
    """目标不存在时先复制一份源资产当容器（材质槽一并带过来；本版没有 StaticMeshFactoryNew）。"""
    target = unreal.EditorAssetLibrary.load_asset(target_path) or unreal.load_asset(target_path)
    if target:
        return target
    unreal.EditorAssetLibrary.make_directory(target_path.rsplit("/", 1)[0])
    unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
    return unreal.EditorAssetLibrary.load_asset(target_path) or unreal.load_asset(target_path)


def bake_pack_leaf():
    """单扇门的门扇模型（SM_Door）→ 双开门一扇：逐轴缩放 + 把手转向 +Y + 包围盒居中。

    尺寸：X 不缩放（板厚保持 5 cm ＝ 2×LeafHalfThicknessCm），Y → 91.5、Z → LEAF_H（一扇的洞口格）。
    """
    source, dm = load_dynamic(PACK_LEAF)
    if not dm:
        LOG.append(("load_pack_leaf", False))
        log("包门扇读取失败：%s" % PACK_LEAF)
        return None
    bb = source.get_bounds()
    native = (bb.box_extent.x * 2.0, bb.box_extent.y * 2.0, bb.box_extent.z * 2.0)
    scale = (1.0, LEAF_W / native[1], LEAF_H / native[2])
    log("leaf 源 %s %.2f×%.2f×%.2f → 目标 %.2f×%.2f×%.2f 缩放 %.4f/%.4f/%.4f" % (
        PACK_LEAF.rsplit("/", 1)[-1], native[0], native[1], native[2],
        native[0] * scale[0], LEAF_W, LEAF_H, scale[0], scale[1], scale[2]))
    MT = unreal.GeometryScript_MeshTransforms
    dm = MT.scale_mesh(dm, unreal.Vector(scale[0], scale[1], scale[2]), unreal.Vector(0.0, 0.0, 0.0), True)
    # 包门扇的把手在网格 −Y；绕 Z 转 180° 后落在 +Y，与基类"把手 +Y／右扇转 180°"的约定一致。
    dm = MT.rotate_mesh(dm, unreal.Rotator(0.0, 0.0, 180.0), unreal.Vector(0.0, 0.0, 0.0))
    # Rz180 把包围盒中心的 X／Y 取反、Z 不变；再平移回去，让包围盒中心＝网格原点。
    centre = unreal.Vector(-bb.origin.x * scale[0], -bb.origin.y * scale[1], bb.origin.z * scale[2])
    dm = MT.translate_mesh(dm, unreal.Vector(-centre.x, -centre.y, -centre.z))
    target = ensure_asset(PACK_LEAF, LEAF_PATH)
    if not target:
        LOG.append(("create_leaf", False))
        return None
    _, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
        dm, target, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD(), True)
    ok = "fail" not in str(outcome).lower()
    LOG.append(("copy_leaf", ok))
    log("leaf copy_to_static outcome=%s" % outcome)
    slots = copy_material_slots(source, target)
    log("leaf 材质槽：源 %d → 目标 %d" % (len(source.get_editor_property("static_materials") or []), slots))
    unreal.EditorAssetLibrary.save_loaded_asset(target, True)
    time.sleep(1.0)
    # 门扇是实体薄板：AlignedBoxes（每个连通体一个盒），与自建门扇同一口径。
    SV.generate_collision(LEAF_PATH, "AlignedBoxes", 1, 25, True)
    asset = unreal.EditorAssetLibrary.load_asset(LEAF_PATH) or unreal.load_asset(LEAF_PATH)
    if not asset:
        LOG.append(("reload_leaf", False))
        return None
    bb2 = asset.get_bounds()
    body = asset.get_editor_property("body_setup")
    geom = body.get_editor_property("agg_geom") if body else None
    log("leaf: bbox %.2f × %.2f × %.2f origin=(%.2f, %.2f, %.2f) tris=%d slots=%d box=%d convex=%d" % (
        bb2.box_extent.x * 2, bb2.box_extent.y * 2, bb2.box_extent.z * 2,
        bb2.origin.x, bb2.origin.y, bb2.origin.z, asset.get_num_triangles(0),
        len(asset.get_editor_property("static_materials") or []),
        len(geom.get_editor_property("box_elems")) if geom else -1,
        len(geom.get_editor_property("convex_elems")) if geom else -1))
    LOG.append(("leaf_origin_centred", abs(bb2.origin.x) < 0.1 and abs(bb2.origin.y) < 0.1 and
                                          abs(bb2.origin.z) < 0.1))
    LOG.append(("leaf_slots_kept",
                len(asset.get_editor_property("static_materials") or []) ==
                len(source.get_editor_property("static_materials") or [])))
    return (round(bb2.box_extent.x * 2, 2), round(bb2.box_extent.y * 2, 2), round(bb2.box_extent.z * 2, 2))


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


def finish(handle, path, label):
    """UV → 存盘 → 碰撞 → 材质 → 读回包围盒。"""
    SV.auto_uv(handle, "XAtlas", 0)
    unreal.EditorAssetLibrary.make_directory(DIR)
    SV.save_mesh_to_static_mesh(handle, path, True, True, False, True)
    SV.release_mesh(handle)
    time.sleep(1.0)
    stamp = disk(path)
    if not stamp:
        log("%s: 存盘后找不到资产 %s" % (label, path))
        return None
    # AlignedBoxes：每个闭合盒体一个盒。ConvexHulls 会把门洞堵死，不能用。
    SV.generate_collision(path, "AlignedBoxes", 1, 25, True)
    SV.set_asset_materials(path, MATERIAL, True)
    asset = unreal.EditorAssetLibrary.load_asset(path)
    bb = asset.get_bounds()
    log("%s: %d B / %s · bbox %.1f x %.1f x %.1f origin=(%.1f, %.1f, %.1f) tris=%d" % (
        label, stamp[0], stamp[1], bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2,
        bb.origin.x, bb.origin.y, bb.origin.z, asset.get_num_triangles(0)))
    return (round(bb.box_extent.x * 2, 1), round(bb.box_extent.y * 2, 1), round(bb.box_extent.z * 2, 1))


def dump_obj(path, out_file, label):
    """三角形汤 OBJ（离线渲染用，不依赖 RHI）。"""
    loaded = SV.load_mesh_from_static_mesh(path, 0)
    dm = SV.get_dynamic_mesh(getattr(loaded, "handle", None))
    print("[dump] %s verts=%d tris=%d closed=%s open_edges=%d comps=%d" % (
        label, dm.get_vertex_count(), dm.get_triangle_count(), dm.get_is_closed_mesh(),
        dm.get_num_open_border_edges(), dm.get_num_connected_components()))
    _, tlist, _ = dm.get_all_triangle_i_ds()
    tarr = tlist.convert_index_list_to_array()
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        f.write("# %s triangle soup\n" % label)
        fi = 0
        for tid in tarr:
            ok, v1, v2, v3 = dm.get_triangle_positions(int(tid))
            fn, ok2 = dm.get_triangle_face_normal(int(tid))
            fi += 1
            f.write("v %.4f %.4f %.4f\n" % (v1.x, v1.y, v1.z))
            f.write("v %.4f %.4f %.4f\n" % (v2.x, v2.y, v2.z))
            f.write("v %.4f %.4f %.4f\n" % (v3.x, v3.y, v3.z))
            f.write("vn %.4f %.4f %.4f\n" % (fn.x, fn.y, fn.z))
            base = fi * 3 - 2
            f.write("f %d//%d %d//%d %d//%d\n" % (base, fi, base + 1, fi, base + 2, fi))
    log("dump %s -> %s (%d faces)" % (label, os.path.basename(out_file), len(tarr)))


def material_colors():
    """把三种体素材质的基色抠出来，给离线渲染上色用（与窗同一套口径）。"""
    library = unreal.MaterialEditingLibrary
    out = {}
    for group, path in (("wood", "/Game/Building/Voxels/Rounded/M_Voxel_Wood"),
                        ("stone", "/Game/Building/Voxels/Rounded/M_Voxel_Stone"),
                        ("marble", "/Game/Props/RomanColumn20260915/M_RomanStone_V2")):
        mat = unreal.EditorAssetLibrary.load_asset(path) or unreal.load_asset(path)
        entry = {"path": path, "base_color": None, "source": None, "candidates": []}
        best = None
        try:
            for expr in library.get_material_expressions(mat) or []:
                cls = expr.get_class().get_name()
                value = None
                label = None
                if "VectorParameter" in cls:
                    value = expr.get_editor_property("default_value")
                    label = str(expr.get_editor_property("parameter_name"))
                elif "Constant3Vector" in cls:
                    value = expr.get_editor_property("constant")
                    label = "Constant3Vector"
                if value is None:
                    continue
                rgb = [round(value.r, 4), round(value.g, 4), round(value.b, 4)]
                lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
                entry["candidates"].append([label, rgb, round(lum, 4)])
                hinted = any(h in (label or "").lower() for h in ("color", "base", "body", "stone", "wood"))
                if not (0.04 < lum < 0.97):
                    continue
                score = lum + (0.5 if hinted else 0.0)
                if best is None or score > best[0]:
                    best = (score, label, rgb)
        except Exception as exc:  # noqa: BLE001
            log("%s 表达式遍历失败: %s" % (group, exc))
        if best:
            entry["base_color"] = best[2]
            entry["source"] = best[1]
        out[group] = entry
        log("%-7s base=%s (%s)" % (group, entry["base_color"], entry["source"]))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(COLOR_JSON, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    log("material colors -> %s" % COLOR_JSON)


# ------------------------------------------------------------------ 门框（4 条边梃）
frame = SV.create_mesh().handle
half_z = FRAME_H / 2.0
inner_y = FRAME_W / 2.0 - MEMBER
box(frame, "frame_left", (0.0, -inner_y - MEMBER / 2.0, half_z), (FRAME_DEPTH, MEMBER, FRAME_H))
box(frame, "frame_right", (0.0, inner_y + MEMBER / 2.0, half_z), (FRAME_DEPTH, MEMBER, FRAME_H))
box(frame, "frame_top", (0.0, 0.0, FRAME_H - MEMBER / 2.0), (FRAME_DEPTH, FRAME_W - 2 * MEMBER, MEMBER))
box(frame, "frame_bottom", (0.0, 0.0, MEMBER / 2.0), (FRAME_DEPTH, FRAME_W - 2 * MEMBER, MEMBER))
info = SV.get_mesh_info(frame)
log("frame: tris=%d comps=%d open_edges=%d bbox %.1f x %.1f x %.1f" % (
    info.triangle_count, info.connected_components, info.open_border_edges,
    info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
    info.bounds_max.z - info.bounds_min.z))
frame_size = finish(frame, FRAME_PATH, "SM_DoubleDoorFrame_200")

# ---------------- 门扇：用单扇门的门扇模型（SM_Door）替换，见 bake_pack_leaf()
leaf_size = bake_pack_leaf()


# ----------------------------------------------------- 占格自检（逐轴等于包围盒/20）
def cells(size, label):
    got = tuple(int(round(v / 20.0)) for v in size) if size else None
    want = tuple(max(1, int((v + 19.9) // 20)) for v in size) if size else None
    log("%s 占格=%s（向上取整 %s）%s" % (label, got, want, "OK" if got == want else "MISMATCH"))
    return got


frame_cells = cells(frame_size, "门框")
if leaf_size:
    log("门扇尺寸 %.2f × %.2f × %.2f cm（由门框条目一起摆放，不进调色板）" % leaf_size)

material_colors()
dump_obj(FRAME_PATH, os.path.join(OUT_DIR, "door_frame_200.obj"), "frame")
dump_obj(LEAF_PATH, os.path.join(OUT_DIR, "door_leaf_200.obj"), "leaf")

bad = [entry for entry in LOG if entry[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
for label, ok, msg in bad:
    log("  FAILED %s %s" % (label, msg))
want_frame = (40.0, 200.0, 240.0)
# 门扇的 X 保持源模型的包围盒（板厚 5 ＋ 两面把手凸出），Y／Z 才是本轮的目标尺寸。
want_leaf = (leaf_size[0] if leaf_size else 0.0, 91.5, LEAF_H)
ok = (not bad and frame_size == want_frame and leaf_size == want_leaf and frame_cells == (2, 10, 12))
log("RESULT: %s（门框 %s 期望 %s／门扇 %s 期望 %s）/ 占格 %s" % (
    "PASS" if ok else "CHECK", frame_size, want_frame, leaf_size, want_leaf, frame_cells))
log("门框 %.0f(X) × %.0f(Y) × %.0f(Z)：进深 %.1f 格、高度 %.1f 格；占格 %s（调色板条目按包围盒自动取整）" % (
    FRAME_DEPTH, FRAME_W, FRAME_H, FRAME_DEPTH / 20.0, FRAME_H / 20.0, frame_cells))
