"""200×200 双开门网格：门框 SM_DoubleDoorFrame_200 + 单扇门扇 SM_DoubleDoorLeaf_200（左右两扇共用）。

尺寸口径（cm，20 cm 体素格；2026-09-18 用户指定 2×2 m 双开门）：
  门框 20(X) × 200(Y) × 200(Z) —— 一格厚、十格宽、十格高，占格 (1,10,10)，正好填满墙上挖的 10×10 洞；
  洞口 184 × 184（边梃 8），两组门扇各 91.5 × 183 × 5 对开，中间留 1 cm 缝。
  门扇 = 边梃 10 ＋ 下冒头 20（门扇特征，比窗扇厚一点、下边宽一点）＋ 2 cm 凹面板
        ＋ 靠中缝一侧的**圆形把手**（贯穿杆＋两面圆盘，距门扇底边 1 m＝离地约 1.08 m）。

把手与窗同一套做法：做在网格的 **+Y 侧**，左扇直接用、右扇在 Actor 里绕 Z 转 180°（门扇本体左右对称），
所以只需要一个门扇网格。代价同样是包围盒的 X 半宽含把手凸出，`AColdSteelDoubleDoor` 用名义板厚算铰链深度。

做法与窗／罗马柱一致：`append_box`／`append_cylinder` 拼**闭合盒体**，不做布尔。
碰撞用 AlignedBoxes（每个盒体一个盒），不能用 ConvexHulls——凸包会把 184×184 的洞口整个堵死。

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
FRAME_DEPTH, FRAME_W, FRAME_H = 20.0, 200.0, 200.0
MEMBER = 8.0                      # 门框边梃宽
LEAF_W, LEAF_H, LEAF_T = 91.5, 183.0, 5.0
STILE = 10.0                      # 门扇边梃与上冒头宽
BOTTOM_RAIL = 20.0                # 门扇下冒头宽（门扇特征）
PANEL_T = 2.0                     # 凹面板厚（每面凹 (LEAF_T-PANEL_T)/2）
# --- 圆形把手：网格 +Y 侧、距自由边 HANDLE_INSET，高度用 HANDLE_ABOVE_BOTTOM 从门扇底边往上量。
HANDLE_INSET = 6.0
HANDLE_ABOVE_BOTTOM = 100.0
HANDLE_ROD_R, HANDLE_ROD_SIDES = 1.5, 12
HANDLE_DISC_R, HANDLE_DISC_T, HANDLE_DISC_SIDES = 4.0, 2.0, 16
HANDLE_PROTRUDE = 5.0             # 把手端面距门扇中面的距离（每面凸 2.5 cm）

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


def rod(handle, label, base_x, y, z, radius, length, sides):
    """沿 X 横放的圆柱：base_x 是**底面圆心的 X**，圆柱从那里往 −X 长 length（pitch=+90）。"""
    result = SV.append_cylinder(handle, tf(base_x, y, z, pitch=90.0), radius, length, sides, 0, True, "Base", 0)
    ok = getattr(result, "success", None)
    LOG.append((label, ok, getattr(result, "message", "")))
    log("%-16s base_x=%+.1f y=%+.1f z=%+.1f r=%.1f len=%.1f x=%.1f..%.1f %s" % (
        label, base_x, y, z, radius, length, base_x - length, base_x, ok))
    return result


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

# ---------------- 门扇（两条边梃 + 上冒头 + 下冒头 + 凹面板 + 靠中缝一侧的圆形把手）
leaf = SV.create_mesh().handle
stile_y = LEAF_W / 2.0 - STILE / 2.0
top_rail_z = LEAF_H / 2.0 - STILE / 2.0
bottom_rail_z = -LEAF_H / 2.0 + BOTTOM_RAIL / 2.0
opening_z = (-LEAF_H / 2.0 + BOTTOM_RAIL + LEAF_H / 2.0 - STILE) / 2.0
opening_h = LEAF_H - STILE - BOTTOM_RAIL
box(leaf, "leaf_stile_left", (0.0, -stile_y, 0.0), (LEAF_T, STILE, LEAF_H))
box(leaf, "leaf_stile_right", (0.0, stile_y, 0.0), (LEAF_T, STILE, LEAF_H))
box(leaf, "leaf_rail_top", (0.0, 0.0, top_rail_z), (LEAF_T, LEAF_W - 2 * STILE, STILE))
box(leaf, "leaf_rail_bottom", (0.0, 0.0, bottom_rail_z), (LEAF_T, LEAF_W - 2 * STILE, BOTTOM_RAIL))
box(leaf, "leaf_panel", (0.0, 0.0, opening_z),
    (PANEL_T, LEAF_W - 2 * STILE + 2.0, opening_h + 2.0))
handle_y = LEAF_W / 2.0 - HANDLE_INSET
handle_z = -LEAF_H / 2.0 + HANDLE_ABOVE_BOTTOM
rod(leaf, "handle_rod", HANDLE_PROTRUDE, handle_y, handle_z,
    HANDLE_ROD_R, HANDLE_PROTRUDE * 2.0, HANDLE_ROD_SIDES)
rod(leaf, "handle_disc_outer", HANDLE_PROTRUDE, handle_y, handle_z,
    HANDLE_DISC_R, HANDLE_DISC_T, HANDLE_DISC_SIDES)
rod(leaf, "handle_disc_inner", -(HANDLE_PROTRUDE - HANDLE_DISC_T), handle_y, handle_z,
    HANDLE_DISC_R, HANDLE_DISC_T, HANDLE_DISC_SIDES)
info = SV.get_mesh_info(leaf)
log("leaf: tris=%d comps=%d open_edges=%d bbox %.1f x %.1f x %.1f（X 含把手凸出）洞口 %.1f×%.1f z中心 %.1f" % (
    info.triangle_count, info.connected_components, info.open_border_edges,
    info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
    info.bounds_max.z - info.bounds_min.z, LEAF_W - 2 * STILE, opening_h, opening_z))
leaf_size = finish(leaf, LEAF_PATH, "SM_DoubleDoorLeaf_200")


# ----------------------------------------------------- 占格自检（逐轴等于包围盒/20）
def cells(size, label):
    got = tuple(int(round(v / 20.0)) for v in size) if size else None
    want = tuple(max(1, int((v + 19.9) // 20)) for v in size) if size else None
    log("%s 占格=%s（向上取整 %s）%s" % (label, got, want, "OK" if got == want else "MISMATCH"))
    return got


frame_cells = cells(frame_size, "门框")
log("门扇尺寸 %.1f × %.1f × %.1f cm（由门框条目一起摆放，不进调色板）" % leaf_size)

material_colors()
dump_obj(FRAME_PATH, os.path.join(OUT_DIR, "door_frame_200.obj"), "frame")
dump_obj(LEAF_PATH, os.path.join(OUT_DIR, "door_leaf_200.obj"), "leaf")

bad = [entry for entry in LOG if entry[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
for label, ok, msg in bad:
    log("  FAILED %s %s" % (label, msg))
want_frame, want_leaf = (20.0, 200.0, 200.0), (HANDLE_PROTRUDE * 2.0, 91.5, 183.0)
ok = (not bad and frame_size == want_frame and leaf_size == want_leaf and frame_cells == (1, 10, 10))
log("RESULT: %s（门框 %s 期望 %s／门扇 %s 期望 %s）/ 占格 %s" % (
    "PASS" if ok else "CHECK", frame_size, want_frame, leaf_size, want_leaf, frame_cells))
