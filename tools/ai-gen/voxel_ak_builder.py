#!/usr/bin/env python3
"""原生手搭体素 AK-47/AKM（程序化直接体素搭建，非 AI 网格切分）。

- 默认 4mm 精度（枪长 ~230 体素）；弹匣为 AK 标志性香蕉形（主体前倾 + 底部大半圆弧 + 黄铜底板）。
- 可选 --mag-fine <米>：把弹匣单独按更细精度搭建（如 0.002/0.003），与主枪 4mm 混合导出
  同一个 OBJ —— 即"大+小体素混合"（OBJ 里每个体素都是独立立方体，可任意混尺寸）。
  注意：弹匣 2mm 会把 OBJ 撑到 ~40MB（表面体素）~120MB（实心），仅适合特写/演示。
- 输出带面明暗烘焙的 OBJ（Godot 直连）+ .vox（MagicaVoxel 可开）。

用法：
  python voxel_ak_builder.py --out assets/models/ak/akm_hand_built_v6
  python voxel_ak_builder.py --mag-fine 0.002 --out assets/models/ak/akm_hand_built_v6_fine
"""

import argparse
import numpy as np

from voxelize_glb import compute_ao, extract_surface, write_obj_with_colors, write_vox

WOOD = np.array([150, 98, 48], dtype=np.uint8)
WOOD2 = np.array([112, 70, 38], dtype=np.uint8)
WOOD3 = np.array([82, 50, 26], dtype=np.uint8)
STEEL = np.array([118, 118, 122], dtype=np.uint8)
STEEL2 = np.array([84, 84, 88], dtype=np.uint8)
STEEL3 = np.array([56, 56, 60], dtype=np.uint8)
DARK = np.array([24, 24, 26], dtype=np.uint8)
BRASS = np.array([178, 143, 80], dtype=np.uint8)


def make_target(shape, pitch, origin):
    grid = np.zeros(shape, dtype=bool)
    colors = np.zeros((*shape, 3), dtype=np.uint8)
    return {"grid": grid, "colors": colors, "pitch": pitch, "origin": np.array(origin, dtype=float)}


def _box(t, x0, x1, y0, y1, z0, z1, color):
    g, p, o = t["grid"], t["pitch"], t["origin"]
    xi0 = max(0, int(round((x0 - o[0]) / p)))
    xi1 = min(g.shape[0] - 1, int(round((x1 - o[0]) / p)))
    yi0 = max(0, int(round((y0 - o[1]) / p)))
    yi1 = min(g.shape[1] - 1, int(round((y1 - o[1]) / p)))
    zi0 = max(0, int(round((z0 - o[2]) / p)))
    zi1 = min(g.shape[2] - 1, int(round((z1 - o[2]) / p)))
    g[xi0 : xi1 + 1, yi0 : yi1 + 1, zi0 : zi1 + 1] = True
    t["colors"][xi0 : xi1 + 1, yi0 : yi1 + 1, zi0 : zi1 + 1] = color


def build_body(t):
    """主枪体（不含弹匣）：机匣/枪管/护木/枪托/握把/扳机护圈/照门准星/枪口制退器。"""
    b = _box
    # 机匣 + 防尘盖（接收机加长加高，贴近 AKM 比例）
    b(t, -0.235, 0.085, -0.032, 0.058, -0.032, 0.032, STEEL)
    b(t, -0.235, 0.085, 0.058, 0.070, -0.030, 0.030, STEEL2)  # 防尘盖
    b(t, 0.000, 0.062, 0.050, 0.058, 0.028, 0.032, DARK)      # 抛壳口（右侧）
    b(t, -0.13, 0.02, 0.012, 0.030, -0.040, -0.032, STEEL3)   # 左侧燕尾镜轨
    b(t, 0.045, 0.085, -0.040, -0.032, -0.036, 0.036, STEEL2) # 前部机匣凸台
    b(t, 0.010, 0.055, 0.055, 0.075, -0.030, 0.030, STEEL2)   # 后照门座
    # 枪管（加长）
    b(t, 0.085, 0.42, -0.006, 0.006, -0.008, 0.008, STEEL2)
    # 导气管 + 木护木（上木带散热槽、下木收窄）
    b(t, 0.105, 0.31, 0.018, 0.040, -0.018, 0.018, STEEL)
    b(t, 0.105, 0.31, -0.008, 0.018, -0.022, 0.022, WOOD)
    b(t, 0.105, 0.31, -0.026, -0.008, -0.024, 0.024, WOOD2)
    for i in range(6):
        sx = 0.125 + i * 0.030
        b(t, sx, sx + 0.012, 0.010, 0.018, -0.018, 0.018, WOOD3)  # 散热槽
    b(t, 0.29, 0.31, -0.030, -0.008, -0.024, 0.024, STEEL3)      # 下护木前卡箍
    # 枪托（加长到 -0.50，尾部收窄锥形 + 金属底板）
    b(t, -0.50, -0.235, -0.022, 0.058, -0.016, 0.016, WOOD)
    b(t, -0.50, -0.42, -0.020, 0.056, -0.012, 0.012, WOOD2)
    b(t, -0.505, -0.495, -0.034, 0.066, -0.016, 0.016, STEEL2)   # 底板
    # 握把（前倾：越往下越靠近枪口，分片阶梯近似）
    for gx0, gx1, gy0, gy1 in [
        (-0.215, -0.160, -0.055, -0.020),
        (-0.210, -0.155, -0.090, -0.055),
        (-0.200, -0.145, -0.125, -0.090),
        (-0.185, -0.130, -0.160, -0.125),
    ]:
        b(t, gx0, gx1, gy0, gy1, -0.016, 0.016, WOOD2)
    b(t, -0.225, -0.215, -0.020, 0.055, -0.018, 0.018, WOOD3)   # 握把后缘加厚
    # 扳机护圈（弹匣后方，底梁带浅弧）
    b(t, -0.170, -0.105, -0.142, -0.128, -0.012, 0.012, DARK)
    b(t, -0.160, -0.110, -0.152, -0.142, -0.010, 0.010, DARK)   # 弧段
    b(t, -0.170, -0.105, -0.142, -0.030, -0.020, -0.012, DARK)  # 左壁
    b(t, -0.170, -0.105, -0.142, -0.030, 0.012, 0.020, DARK)    # 右壁
    b(t, -0.135, -0.115, -0.100, -0.070, -0.010, 0.010, DARK)   # 扳机
    # 拉机柄（右侧）
    b(t, -0.195, -0.145, 0.042, 0.058, 0.030, 0.042, STEEL3)
    # 机匣右侧铆钉列
    for rx in (-0.205, -0.165, -0.125, -0.06, 0.00):
        b(t, rx - 0.003, rx + 0.003, 0.022, 0.032, 0.030, 0.034, STEEL3)
    # 后照门（加高到 0.120）+ 缺口
    b(t, 0.020, 0.055, 0.070, 0.120, -0.028, 0.028, STEEL2)
    b(t, 0.030, 0.045, 0.104, 0.120, -0.007, 0.007, DARK)
    # 前准星（立柱更高 + 护翼）
    b(t, 0.300, 0.330, 0.008, 0.115, -0.010, 0.010, STEEL2)
    b(t, 0.300, 0.330, 0.104, 0.115, -0.005, 0.005, DARK)
    b(t, 0.304, 0.328, 0.048, 0.115, -0.028, -0.016, STEEL)
    b(t, 0.304, 0.328, 0.048, 0.115, 0.016, 0.028, STEEL)
    # 枪口制退器（加长 + 三向侧槽 + 口圈）
    b(t, 0.42, 0.50, -0.013, 0.013, -0.013, 0.013, STEEL2)
    b(t, 0.43, 0.47, 0.010, 0.013, -0.013, 0.013, DARK)
    b(t, 0.43, 0.47, -0.013, -0.010, -0.013, 0.013, DARK)
    b(t, 0.43, 0.47, -0.013, 0.013, 0.010, 0.013, DARK)
    b(t, 0.49, 0.50, -0.013, 0.013, -0.013, 0.013, STEEL3)     # 口圈


def build_mag(t):
    """香蕉形弹匣：主体前倾 + 底部大半圆弧 + 黄铜底板。"""
    b = _box
    p = t["pitch"]
    # 顶部卡笋 + 后突耳（嵌入机匣底）
    b(t, -0.100, -0.045, -0.050, -0.038, -0.020, 0.020, STEEL2)
    b(t, -0.110, -0.085, -0.070, -0.050, -0.018, 0.018, STEEL3)
    # 主体：y -0.050（顶）→ -0.280（底），前缘后倒 ~24°，后缘微倾，侧向微收
    y0, y1 = -0.050, -0.280
    n = max(4, int(round((y1 - y0) / p)))
    for i in range(n):
        y = y0 + (y1 - y0) * i / max(1, n - 1)
        u = (y - y0) / (y1 - y0)
        xf = 0.030 - 0.105 * u
        xb = -0.075 - 0.035 * u
        zw = 0.021 - 0.003 * u
        col = STEEL if u < 0.65 else STEEL2
        b(t, xb, xf, y - p / 2, y + p / 2, -zw, zw, col)
    # 底部大半圆弧：半径 50mm，从 (x=-0.075, y=-0.28) 圆滑到 (x=-0.175, y=-0.28)，
    # 最低点 y=-0.33；尾部自然上收形成"香蕉尖"。
    xc, yc, r = -0.125, -0.280, 0.050
    ny = max(4, int(round(r / p)))
    for i in range(ny):
        dy = r * i / max(1, ny - 1)
        y = yc - dy
        h = np.sqrt(max(0.0, r * r - dy * dy))
        col = BRASS if dy > r * 0.55 else STEEL3
        b(t, xc - h, xc + h, y - p / 2, y + p / 2, -0.020, 0.020, col)


def grid_to_palette(grid, colors):
    uniq = np.unique(colors[grid].reshape(-1, 3), axis=0)
    # 与 voxelize_glb 约定一致：索引 1..N，调色板不含黑色槽（0 号槽保留给"空"）。
    # 这样 write_obj_with_colors 的 pal[c-1] 和 write_vox 的 pal[1:]=palette[:] 都正确。
    palette = uniq
    indices = np.zeros(grid.shape, dtype=np.uint8)
    for i in range(len(palette)):
        sel = (
            (colors[..., 0] == palette[i][0])
            & (colors[..., 1] == palette[i][1])
            & (colors[..., 2] == palette[i][2])
        )
        indices[sel] = i + 1
    indices[~grid] = 0
    return indices, palette


def main() -> int:
    ap = argparse.ArgumentParser(description="手搭体素 AK（原生搭建，解剖正确）")
    ap.add_argument("--pitch", type=float, default=0.004, help="主枪体素边长（米），默认 4mm")
    ap.add_argument(
        "--mag-fine",
        type=float,
        default=0.0,
        help="弹匣细分精度（米），>0 时弹匣按该精度与主枪混合导出（大小体素），0=与主枪同精度",
    )
    ap.add_argument("--out", default="assets/models/ak/akm_hand_built")
    args = ap.parse_args()

    pitch = args.pitch
    nx = int(round(1.00 / pitch)) + 1
    ny = int(round(0.72 / pitch)) + 1
    nz = int(round(0.10 / pitch)) + 1
    shape = (nx, ny, nz)
    origin = (-nx * pitch / 2.0, -ny * pitch / 2.0, -nz * pitch / 2.0)

    # .vox 用粗网格（含弹匣，MagicaVoxel 固定网格）
    coarse_vox = make_target(shape, pitch, origin)
    build_body(coarse_vox)
    build_mag(coarse_vox)
    print("coarse filled voxels:", int(coarse_vox["grid"].sum()))

    extras = None
    if args.mag_fine > 0:
        fp = args.mag_fine
        xmin, ymin, zmin = -0.19, -0.37, -0.02
        fshape = (
            int(round(0.26 / fp)) + 1,
            int(round(0.36 / fp)) + 1,
            int(round(0.06 / fp)) + 1,
        )
        fine = make_target(fshape, fp, (xmin, ymin, zmin))
        build_mag(fine)
        print("fine mag filled voxels:", int(fine["grid"].sum()), "at", fp, "m")
        # .obj 用主枪粗网格（不含弹匣）+ 细弹匣，合并导出
        coarse_obj = make_target(shape, pitch, origin)
        build_body(coarse_obj)
        idx_c, pal_c = grid_to_palette(coarse_obj["grid"], coarse_obj["colors"])
        idx_f, pal_f = grid_to_palette(fine["grid"], fine["colors"])
        surf_c = extract_surface(coarse_obj["grid"])
        idx_c[~surf_c] = 0
        surf_f = extract_surface(fine["grid"])
        idx_f[~surf_f] = 0
        ao_c = compute_ao(coarse_obj["grid"])
        ao_f = compute_ao(fine["grid"])
        extras = [(fshape, idx_f, pal_f, fp, (xmin, ymin, zmin), ao_f)]
        write_obj_with_colors(args.out + ".obj", shape, idx_c, pal_c, pitch, ao_c, extras)
    else:
        idx, pal = grid_to_palette(coarse_vox["grid"], coarse_vox["colors"])
        surf = extract_surface(coarse_vox["grid"])
        idx[~surf] = 0
        ao = compute_ao(coarse_vox["grid"])
        write_obj_with_colors(args.out + ".obj", shape, idx, pal, pitch, ao)

    if max(shape) <= 255:
        idx_v, pal_v = grid_to_palette(coarse_vox["grid"], coarse_vox["colors"])
        write_vox(args.out + ".vox", shape, idx_v, pal_v)
    else:
        print("提示：网格轴长超过 255（", shape, "），跳过 .vox（MagicaVoxel 标准世界放不下）")
    print("导出完成:", args.out + ".obj / .vox")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
