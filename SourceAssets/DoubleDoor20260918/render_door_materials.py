"""离线渲染 2×2 m 双开门的几种材质外观（numpy z-buffer + Lambert，不需要引擎／RHI）。

读 build_double_door_meshes_20260918.py 导出的三角汤 OBJ，按与 C++ 同一套铰链数学摆出关／开两种
状态，再分别按木材／石头／大理石上色。相机、光照与体素墙（10×10 落地门洞）都写死在脚本里。
本文件与窗的渲染脚本同源（窗见 SourceAssets/Window20260918/render_window_materials.py），
差别只在尺寸常量、洞口位置与相机。

运行：python SourceAssets/DoubleDoor20260918/render_door_materials.py
"""

import json
import math
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "preview_20260918")
COLOR_JSON = os.path.join(DIR, "material_colors.json")

# 门的装配尺寸（cm），必须与 ColdSteelDoubleDoor.cpp / build_double_door_meshes 保持一致。
FRAME_W, FRAME_H, FRAME_DEPTH = 200.0, 200.0, 40.0   # 进深 40 与单扇门统一（2026-09-18）
MEMBER = 8.0
LEAF_HALF_W = 91.5 / 2.0
LEAF_HALF_T = 14.92               # 门扇 X 包围盒的一半（包里 SM_Door 缩放版 29.8）
OPEN_ANGLE = 85.0                 # 与 C++ 的 OpenAngleDegrees 一致（贯通把手的摆向侧会扫框，收 5°）

SKY_TOP = np.array([0.36, 0.52, 0.74])
SKY_BOT = np.array([0.72, 0.78, 0.84])
# 光从相机那一侧斜上方来（窗的进深轴是 X，主视角在 +X 侧），否则正对相机的面全是环境光。
LIGHT = np.array([0.45, -0.52, 0.72])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
# 参照墙用明显偏冷的深灰：石头／大理石窗与墙同色系时仍看得清轮廓。
WALL_COLOR = np.array([0.40, 0.42, 0.45])
FALLBACK = {"wood": np.array([0.44, 0.28, 0.15]),
            "stone": np.array([0.53, 0.51, 0.47]),
            "marble": np.array([0.87, 0.86, 0.82])}


def load_obj(name):
    verts = []
    for line in open(os.path.join(DIR, name)):
        t = line.split()
        if t and t[0] == "v":
            verts.append((float(t[1]), float(t[2]), float(t[3])))
    return np.array(verts, dtype=float).reshape(-1, 3, 3)


def rot_z(points, degrees):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    out = points.copy()
    out[..., 0] = points[..., 0] * c - points[..., 1] * s
    out[..., 1] = points[..., 0] * s + points[..., 1] * c
    return out


def at(tris, x=0.0, y=0.0, z=0.0):
    return tris + np.array([x, y, z], dtype=float)


def actor_space(tris):
    """对齐到 Actor 的摆放口径（与 C++ 的 AlignGeometry 一致）：包围盒 X／Y 居中、底面落在 z=0。
    门扇现在是包里 SM_Door 的缩放版，pivot 在边上／底边，不先摆正会整体偏移。"""
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    return tris - np.array([(lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0, lo[2]])


def assemble(frame, leaf, angle=0.0, swing=1.0, lift=0.0, report=None):
    """按 C++ 的铰链口径摆门：铰链贴门扇外／内侧面，两扇同向对开。
    窗族（含双开门）的门扇口径是**包围盒中心落在铰链目标点**（与 AColdSteelWindow 一致），
    所以这里把门扇按包围盒中心归零，而不是像单扇门那样底面对齐。"""
    out = [at(actor_space(frame), 0.0, 0.0, lift)]
    lo, hi = leaf.reshape(-1, 3).min(axis=0), leaf.reshape(-1, 3).max(axis=0)
    leaf = leaf - (lo + hi) / 2.0
    hinge_x = swing * LEAF_HALF_T
    opening_half_y = FRAME_W / 2.0 - MEMBER
    for side in (-1.0, 1.0):                    # 左扇铰在 −Y，右扇铰在 +Y
        hinge = np.array([hinge_x, side * opening_half_y, FRAME_H / 2.0 + lift])
        centre_offset = np.array([-hinge_x, -side * LEAF_HALF_W, 0.0])
        # 包里的 SM_Door 门把在网格 **−Y** 侧：左扇要整体转 180°（自由边朝洞口中间），与 Actor 一致。
        body = rot_z(leaf, 180.0) if side < 0.0 else leaf
        # 与 C++ 同号：左扇 −swing·θ、右扇 +swing·θ（两扇因此朝同一侧开）。
        leaf_angle = side * swing * angle
        rotated = rot_z(body + centre_offset, leaf_angle)
        placed = rotated + hinge
        if report:
            lo, hi = placed.reshape(-1, 3).min(axis=0), placed.reshape(-1, 3).max(axis=0)
            print("    %s扇角=%+6.1f  铰链X=%+.0f  x=%.1f..%.1f  y=%.1f..%.1f  z=%.1f..%.1f" % (
                report, leaf_angle, hinge_x, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
        out.append(placed)
    return out


def wall(hole_y=(-100.0, 100.0), hole_z=(0.0, 200.0)):
    """一层 20 cm 体素墙（正对着门开一个 10×10、落地的洞），给门一个尺度参照。
    格锚点按洞口起点对齐（洞口起点落在 20 cm 网格上），否则洞边会压在格子中间、露半块砖缝。
    墙要比洞口高出两格，否则窗顶与墙顶齐平、看起来像墙上缺了一块。"""
    boxes = []
    for iy in range(-2, 12):                    # 洞口两侧各留两格
        y0 = hole_y[0] + 20.0 * iy
        for iz in range(0, 13):                # 洞口下方三格（到地面）、上方两格
            z0 = hole_z[0] + 20.0 * iz
            if hole_y[0] <= y0 and y0 + 20.0 <= hole_y[1] and hole_z[0] <= z0 and z0 + 20.0 <= hole_z[1]:
                continue
            boxes.append(cell_box(0.0, y0 + 10.0, z0 + 10.0, 20.0, 19.6, 19.6, iy * 7 + iz * 13))
    return boxes


def cell_box(cx, cy, cz, sx, sy, sz, seed):
    """轴对齐盒体的 12 个三角形（外侧朝向正确即可，渲染时按面法线剔除背面）。"""
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    corner = np.array([[cx - hx, cy - hy, cz - hz], [cx + hx, cy - hy, cz - hz],
                       [cx + hx, cy + hy, cz - hz], [cx - hx, cy + hy, cz - hz],
                       [cx - hx, cy - hy, cz + hz], [cx + hx, cy - hy, cz + hz],
                       [cx + hx, cy + hy, cz + hz], [cx - hx, cy + hy, cz + hz]])
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]
    tris = np.array([[corner[a], corner[b], corner[c]] for a, b, c in faces])
    tris[:, 0, 0] += (seed % 5) * 0.03          # 每块体素轻微错位，读得出"砌"的痕迹
    return tris


def tint(group, centroid, normal):
    """按材质给每张面上纹理提示：木材顺纹、石头斑驳、大理石纹路。"""
    x, y, z = centroid
    if group == "wood":
        along = z if abs(normal[2]) < 0.6 else y
        grain = 0.5 + 0.5 * math.sin(along * 0.55) * math.sin(along * 0.17 + 1.1)
        return 0.86 + 0.20 * grain
    if group == "stone":
        blotch = 0.5 + 0.5 * math.sin(x * 0.9 + y * 0.7) * math.sin(z * 1.3 + 0.6)
        speck = 0.5 + 0.5 * math.sin(x * 3.1) * math.sin(y * 2.7) * math.sin(z * 3.3)
        return 0.88 + 0.16 * blotch + 0.08 * speck
    vein = abs(math.sin((x * 0.30 + y * 0.18 + z * 0.42) * 2.1))
    return 0.92 + 0.10 * (1.0 - vein) ** 6 + 0.05 * math.sin(z * 0.8)


def render(tris_list, color, group, cam, target, width=860, height=640, fov=44.0, ambient=0.34,
           wall_tris=None):
    tris = np.concatenate(tris_list, axis=0)
    cam = np.array(cam, dtype=float)
    fwd = np.array(target, dtype=float) - cam
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)

    def prep(stack):
        centroid = stack.mean(axis=1)
        normal = np.cross(stack[:, 1] - stack[:, 0], stack[:, 2] - stack[:, 0])
        area = np.linalg.norm(normal, axis=1)
        good = area > 1e-9
        normal = normal[good] / area[good][:, None]
        return stack[good], centroid[good], normal

    tris, centroid, normal = prep(tris)
    view = cam - centroid
    cosang = (normal * view).sum(axis=1) / (np.linalg.norm(view, axis=1) + 1e-9)
    keep = cosang > -0.05
    tris, centroid, normal = tris[keep], centroid[keep], normal[keep]

    shade = ambient + (1.0 - ambient) * np.clip(normal @ LIGHT, 0.0, 1.0)
    face_color = np.clip(color[None, :] * shade[:, None] *
                         np.array([tint(group, c, n) for c, n in zip(centroid, normal)])[:, None], 0.0, 1.0)

    if wall_tris is not None:
        wall_stack = np.concatenate(wall_tris, axis=0)
        wtris, wcentroid, wnormal = prep(wall_stack)
        wview = cam - wcentroid
        wcos = (wnormal * wview).sum(axis=1) / (np.linalg.norm(wview, axis=1) + 1e-9)
        keep = wcos > -0.05
        wtris, wcentroid, wnormal = wtris[keep], wcentroid[keep], wnormal[keep]
        wshade = ambient + (1.0 - ambient) * np.clip(wnormal @ LIGHT, 0.0, 1.0)
        wcolor = np.clip(WALL_COLOR[None, :] * wshade[:, None] * 0.98, 0.0, 1.0)
        tris = np.concatenate([tris, wtris], axis=0)
        face_color = np.concatenate([face_color, wcolor], axis=0)

    rel = tris - cam
    cx = (rel * right).sum(axis=-1)
    cy = (rel * up).sum(axis=-1)
    cz = (rel * fwd).sum(axis=-1)
    z_face = cz.mean(axis=1)
    f = (width * 0.5) / math.tan(math.radians(fov) * 0.5)
    sx = cx * f / np.maximum(cz, 1e-6) + width * 0.5
    sy = height * 0.5 - cy * f / np.maximum(cz, 1e-6)

    grad = np.linspace(0.0, 1.0, height)[:, None, None]
    image = SKY_TOP * (1 - grad) + SKY_BOT * grad
    image = np.repeat(image, width, axis=1)
    zbuf = np.full((height, width), np.inf)

    for i in np.argsort(-z_face):
        xs, ys = sx[i], sy[i]
        x0, x1 = int(max(0, math.floor(xs.min()))), int(min(width - 1, math.ceil(xs.max())))
        y0, y1 = int(max(0, math.floor(ys.min()))), int(min(height - 1, math.ceil(ys.max())))
        if x1 < x0 or y1 < y0:
            continue
        denom = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(denom) < 1e-9:
            continue
        px = np.arange(x0, x1 + 1) + 0.5
        py = np.arange(y0, y1 + 1) + 0.5
        PX, PY = np.meshgrid(px, py)
        w0 = ((ys[1] - ys[2]) * (PX - xs[2]) + (xs[2] - xs[1]) * (PY - ys[2])) / denom
        w1 = ((ys[2] - ys[0]) * (PX - xs[2]) + (xs[0] - xs[2]) * (PY - ys[2])) / denom
        w2 = 1.0 - w0 - w1
        mask = (w0 > -0.003) & (w1 > -0.003) & (w2 > -0.003)
        if not mask.any():
            continue
        # 逐像素深度：整面共用一个深度会让 20 cm 进深的洞口侧壁与窗扇互相遮错。
        zdepth = w0 * cz[i][0] + w1 * cz[i][1] + w2 * cz[i][2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        closer = mask & (zdepth > 15.0) & (zdepth < sub)
        if not closer.any():
            continue
        sub[closer] = zdepth[closer]
        image[y0:y1 + 1, x0:x1 + 1][closer] = face_color[i]
    return (np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)


def save(name, array):
    Image.fromarray(array).save(os.path.join(DIR, name))
    print("    wrote %s" % name)


def material_colors():
    """优先用引擎里读出来的材质基色；读不到退回手写的近似色。"""
    colors = dict(FALLBACK)
    if os.path.exists(COLOR_JSON):
        data = json.load(open(COLOR_JSON, encoding="utf-8"))
        for group, entry in data.items():
            rgb = entry.get("base_color")
            if rgb:
                colors[group] = np.array(rgb, dtype=float)
                print("  %s base color=%s（来自 %s）" % (group, rgb, entry.get("source")))
            else:
                print("  %s: 材质里没有可直接用的基色，用近似色 %s" % (group, np.round(colors[group], 3)))
    return colors


print("== 载入 ==")
os.makedirs(DIR, exist_ok=True)
frame = load_obj("door_frame_200.obj")


def check_mesh(name, tris, want):
    """尺寸自检：OBJ 与当前尺寸不符时直接报错（窗的渲染脚本就踩过一次"框是旧版"）。"""
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    got = tuple(round(float(v), 1) for v in (hi - lo))
    print("  %-18s bbox %.1f x %.1f x %.1f  期望 %s  %s" % (
        name, got[0], got[1], got[2], want, "OK" if got == want else "MISMATCH"))
    assert got == want, "%s 的 OBJ 与当前尺寸不符：%s" % (name, got)


leaf = load_obj("door_leaf_200.obj")
print("  frame faces=%d leaf faces=%d" % (len(frame), len(leaf)))
check_mesh("door_frame", frame, (FRAME_DEPTH, FRAME_W, FRAME_H))
check_mesh("door_leaf", leaf, (29.8, 91.5, 183.0))
COLORS = material_colors()

print("== 装配自检（各扇的世界包围盒，cm）==")
CLOSED = assemble(frame, leaf, 0.0, 1.0, lift=0.0, report="关·")
OPEN = assemble(frame, leaf, OPEN_ANGLE, 1.0, lift=0.0, report="开外")
OPEN_IN = assemble(frame, leaf, OPEN_ANGLE, -1.0, lift=0.0, report="开内")
WALL = wall()
stack = np.concatenate(CLOSED, axis=0)
lo, hi = stack.reshape(-1, 3).min(axis=0), stack.reshape(-1, 3).max(axis=0)
print("  门 bbox %.0f x %.0f x %.0f，z %.0f..%.0f（门洞落地）" % (
    hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], lo[2], hi[2]))

print("== 三种材质：关门（3/4 视角，含 10×10 落地门洞的体素墙）==")
# 窗的进深轴是 X：主视角放在 +X 侧（墙外面），稍微带一点 −Y 看立体感。
FRONT_CAM = (560.0, -430.0, 320.0)
FRONT_TARGET = (0.0, 0.0, 110.0)
shots = {}
for group in ("wood", "stone", "marble"):
    image = render(CLOSED, COLORS[group], group, FRONT_CAM, FRONT_TARGET, 880, 800, 34.0, wall_tris=WALL)
    name = "door_%s_closed.png" % group
    save(name, image)
    shots[group] = image

print("== 正视图：只看门（石材，去掉墙，便于读门框与两扇的比例）==")
save("door_stone_isolated.png", render(CLOSED, COLORS["stone"], "stone", (820.0, 0.0, 105.0),
                                       (0.0, 0.0, 105.0), 820, 900, 22.0))
print("== 正视图：含墙（石材）==")
save("door_stone_front.png", render(CLOSED, COLORS["stone"], "stone", (980.0, 0.0, 130.0),
                                    (0.0, 0.0, 130.0), 820, 900, 26.0, wall_tris=WALL))
print("== 内侧视角（大理石，从 −X 看向室内那一面）==")
save("door_marble_inside.png", render(CLOSED, COLORS["marble"], "marble", (-820.0, -430.0, 350.0),
                                      (0.0, 0.0, 120.0), 880, 800, 32.0, wall_tris=WALL))

print("== 开门状态：只看门（大理石，向外开；读两扇的摆向与铰链位置）==")
save("door_marble_open_isolated.png", render(OPEN, COLORS["marble"], "marble", (660.0, -520.0, 350.0),
                                             (0.0, 0.0, 115.0), 880, 800, 34.0))
print("== 开门状态：含墙（大理石，向外开）==")
save("door_marble_open.png", render(OPEN, COLORS["marble"], "marble", (760.0, -560.0, 380.0),
                                    (0.0, 0.0, 115.0), 880, 800, 34.0, wall_tris=WALL))
print("== 开门状态：含墙（木材，向内开，玩家在室外侧的对照）==")
save("door_wood_open_inward.png", render(OPEN_IN, COLORS["wood"], "wood", (760.0, -560.0, 380.0),
                                         (0.0, 0.0, 115.0), 880, 800, 34.0, wall_tris=WALL))

print("== 开门状态：俯视角（木材，向外开；看清两扇各自绕外侧铰链转出去）==")
save("door_wood_open_top.png", render(OPEN, COLORS["wood"], "wood", (320.0, -760.0, 980.0),
                                      (0.0, 0.0, 120.0), 880, 800, 34.0, wall_tris=WALL))
print("== 中缝特写（大理石，只看把手与两扇交界）==")
save("door_marble_handle_detail.png", render(CLOSED, COLORS["marble"], "marble", (300.0, -120.0, 150.0),
                                             (0.0, 0.0, 108.0), 900, 760, 20.0))
print("== 拼一张材质对照表 ==")
sheet = Image.new("RGB", (880, 800 * 3 + 24), (28, 30, 33))
for index, group in enumerate(("wood", "stone", "marble")):
    sheet.paste(Image.fromarray(shots[group]), (0, index * (800 + 8)))
sheet.save(os.path.join(DIR, "door_material_sheet.png"))
print("    wrote door_material_sheet.png")
print("RESULT: PASS")
