# render_ingot_icons.py — 金属锭背包图标离线渲染（2026-10-01）
#
# 背景：金属锭改占格 2x1 横放后，运行时捕获通道 ColdSteelMaterialIcon.cpp
# PrepareMaterial 仍按同一公式出图（绕 Z 偏航 60°、绕 Y 俯仰 -45°——正角会
# 把远端压下让相机看到底面，从上往下取景要负角——正交取景、主轴填满 91%）；
# 本脚本离线复刻同一取景，把 Content/ColdSteelData/Icons/ 下的目录回退图
# 重出为 640x320 透明 PNG，四种金属色与 build_ingot_assets_ue.py 的
# INGOTS 表一致（linear -> sRGB）。
#
# 运行：python Tools/Smelting/render_ingot_icons.py
# 依赖：Blender（只做一次 FBX->OBJ 转换）、numpy、Pillow。

import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FBX = os.path.join(BASE, 'Saved', 'IngotPipeline', 'SM_Ingot.fbx')
BLENDER = r'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
ICONS = os.path.join(BASE, 'Content', 'ColdSteelData', 'Icons')

# 与 build_ingot_assets_ue.py INGOTS 一致的线性 Tint（Metallic=1.0 不参与离线着色）。
INGOTS = {
    'ironIngot': (0.55, 0.56, 0.60),
    'copperIngot': (0.75, 0.33, 0.19),
    'silverIngot': (0.85, 0.88, 0.92),
    'goldIngot': (0.93, 0.65, 0.18),
}

W, H, SS = 640, 320, 3          # 2x1 占格 -> 640x320，3x 超采样抗锯齿
YAW_DEG, PITCH_DEG = 60.0, -45.0  # 与 PrepareMaterial 锭类角度一致（负俯仰＝俯视）


def fbx_to_obj():
    obj = os.path.join(tempfile.gettempdir(), 'sm_ingot_icon.obj')
    script = os.path.join(tempfile.gettempdir(), 'sm_ingot_fbx2obj.py')
    with open(script, 'w') as f:
        f.write(
            "import bpy\n"
            "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
            f"bpy.ops.import_scene.fbx(filepath=r'{FBX}')\n"
            f"bpy.ops.wm.obj_export(filepath=r'{obj}')\n"
        )
    subprocess.run([BLENDER, '-b', '--python-exit-code', '1', '--python', script],
                   check=True, capture_output=True, text=True)
    return obj


def load_obj(path):
    verts, faces = [], []
    for line in open(path):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'v':
            verts.append([float(x) for x in parts[1:4]])
        elif parts[0] == 'f':
            idx = [int(p.split('/')[0]) - 1 for p in parts[1:]]
            for i in range(1, len(idx) - 1):  # 扇形三角化
                faces.append([idx[0], idx[i], idx[i + 1]])
    return np.array(verts), np.array(faces)


def to_ue_axes(verts):
    # FBX 往返后轴向以几何为准：最长边＝UE X（拾取物长轴正对相机），
    # 次长＝Y（画面横向），最短＝Z（画面竖向）。铸锭 24x9x5cm 无歧义。
    span = verts.max(0) - verts.min(0)
    order = np.argsort(span)[::-1]
    m = np.zeros((3, 3))
    m[order[0]] = [1, 0, 0]
    m[order[1]] = [0, 1, 0]
    m[order[2]] = [0, 0, 1]
    return verts @ m.T


def srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def render(tint):
    verts, faces = load_obj(OBJ)
    v = to_ue_axes(verts)
    ry = math.radians(PITCH_DEG)
    rz = math.radians(YAW_DEG)
    r = np.array([[math.cos(ry), 0, math.sin(ry)],
                  [0, 1, 0],
                  [-math.sin(ry), 0, math.cos(ry)]]) @ \
        np.array([[math.cos(rz), -math.sin(rz), 0],
                  [math.sin(rz), math.cos(rz), 0],
                  [0, 0, 1]])
    v = v @ r.T

    # 正交取景：与 PrepareMaterial 同口径，主轴填满 91%，轮廓中心对画布中心。
    span_y = v[:, 1].max() - v[:, 1].min()
    span_z = v[:, 2].max() - v[:, 2].min()
    ortho_w = max(span_y, span_z * (W / H)) / 0.91
    ppcm = (W * SS) / ortho_w
    sx = (v[:, 1] - (v[:, 1].min() + v[:, 1].max()) * .5) * ppcm + W * SS * .5
    sy = H * SS * .5 - (v[:, 2] - (v[:, 2].min() + v[:, 2].max()) * .5) * ppcm
    depth = v[:, 0]  # 相机在 -X 侧看 +X，近者 X 小

    p0 = v[faces[:, 0]]
    n = np.cross(v[faces[:, 1]] - p0, v[faces[:, 2]] - p0)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    front = n[:, 0] < 0  # 面向相机（-X）的面

    light = np.array([-0.55, 0.35, 0.75])
    light /= np.linalg.norm(light)
    view = np.array([-1.0, 0.0, 0.0])
    half = (light + view) / np.linalg.norm(light + view)
    base = np.array([srgb(c) for c in tint])

    img = np.zeros((H * SS, W * SS, 4), np.float32)
    zbuf = np.full((H * SS, W * SS), np.inf)
    xs = np.stack([sx[faces[:, i]] for i in range(3)], 1)
    ys = np.stack([sy[faces[:, i]] for i in range(3)], 1)
    zs = np.stack([depth[faces[:, i]] for i in range(3)], 1)
    ys_int = np.arange(H * SS)[:, None]
    xs_int = np.arange(W * SS)[None, :]

    for t in np.where(front)[0]:
        x0, x1 = xs[t].min(), xs[t].max()
        y0, y1 = ys[t].min(), ys[t].max()
        ix0, ix1 = max(0, int(x0) - 1), min(W * SS, int(x1) + 2)
        iy0, iy1 = max(0, int(y0) - 1), min(H * SS, int(y1) + 2)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        px = xs_int[:, ix0:ix1] + .5
        py = ys_int[iy0:iy1, :] + .5
        a, b, c = (xs[t, 0], ys[t, 0]), (xs[t, 1], ys[t, 1]), (xs[t, 2], ys[t, 2])
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l0 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / d
        l1 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / d
        l2 = 1 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        if not inside.any():
            continue
        z = l0 * zs[t, 0] + l1 * zs[t, 1] + l2 * zs[t, 2]
        zb = zbuf[iy0:iy1, ix0:ix1]
        hit = inside & (z < zb)
        if not hit.any():
            continue
        zb[hit] = z[hit]
        lam = max(0.0, float(n[t] @ light))
        spec = max(0.0, float(n[t] @ half)) ** 14
        col = np.clip(base * (0.30 + 0.85 * lam) + spec * 0.28, 0, 1)
        tile = img[iy0:iy1, ix0:ix1]
        tile[hit, 0:3] = col * 255
        tile[hit, 3] = 255

    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return out.resize((W, H), Image.LANCZOS)


OBJ = fbx_to_obj()
for name, tint in INGOTS.items():
    icon = render(tint)
    dst = os.path.join(ICONS, name + '.png')
    icon.save(dst)
    a = np.asarray(icon)[:, :, 3]
    ys, xs = np.where(a > 8)
    fill = 100.0 * (ys.max() - ys.min() + 1) / H
    print(f'{name}: {icon.width}x{icon.height} bbox=({xs.min()},{ys.min()})-'
          f'({xs.max()},{ys.max()}) fill_h={fill:.1f}% -> {dst}')
