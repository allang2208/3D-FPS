#!/usr/bin/env python3
"""GLB → 高精度体素（.vox + 顶点色 OBJ）

把 AI 生成的枪模（TRELLIS/混元 GLB）体素化为"体素像素"风格：
  - 0.5cm 精度（默认），枪长 ~200 格，属高精度体素；
  - 颜色从网格贴图按最近表面点 UV 采样，再量化到 <=256 色调色板；
  - 输出 .vox（MagicaVoxel 原生，用于手工精修=方案B）和带顶点色的 .obj（Godot 直连预览）。

用法：
  python voxelize_glb.py --input assets/models/akm_trellis.glb \
      --pitch 0.005 --out assets/models/ak/akm_voxel --palette 96
"""

import argparse
import os
import struct
import time

import numpy as np
import trimesh
from PIL import Image


def load_single_mesh(path: str) -> trimesh.Trimesh:
    scene = trimesh.load(path, force="scene")
    try:
        mesh = scene.to_geometry()
    except Exception:
        mesh = scene.dump(concatenate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("GLB 里没有 Trimesh 网格")
    return mesh


def sample_colors(mesh: trimesh.Trimesh, centers: np.ndarray) -> np.ndarray:
    """按最近表面点采样颜色（优先贴图 UV，其次顶点色，最后灰色）。"""
    n = len(centers)
    out = np.zeros((n, 3), dtype=np.uint8)
    out[:] = (150, 150, 150)
    visual = getattr(mesh, "visual", None)
    if visual is None:
        return out
    if visual.kind == "texture" and visual.uv is not None:
        material = getattr(visual, "material", None)
        img = getattr(material, "baseColorTexture", None) or getattr(material, "image", None)
        if img is not None:
            if not isinstance(img, Image.Image):
                img = Image.open(img)
            img = img.convert("RGB")
            iw, ih = img.size
            uv = np.asarray(visual.uv, dtype=np.float64)
            try:
                pts, _, tri_ids = mesh.nearest.on_surface(centers)
            except Exception:
                return out
            tris = mesh.faces[tri_ids]
            v0 = mesh.vertices[tris[:, 0]]
            v1 = mesh.vertices[tris[:, 1]]
            v2 = mesh.vertices[tris[:, 2]]
            # 重心坐标（面积法，点在平面上稳定）
            area = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
            w0 = np.linalg.norm(np.cross(v1 - pts, v2 - pts), axis=1) / np.maximum(area, 1e-12)
            w1 = np.linalg.norm(np.cross(v2 - pts, v0 - pts), axis=1) / np.maximum(area, 1e-12)
            w2 = 1.0 - w0 - w1
            uv_p = (
                uv[tris[:, 0]] * w0[:, None]
                + uv[tris[:, 1]] * w1[:, None]
                + uv[tris[:, 2]] * w2[:, None]
            )
            px = np.clip((uv_p[:, 0] * (iw - 1)).astype(int), 0, iw - 1)
            py = np.clip(((1.0 - uv_p[:, 1]) * (ih - 1)).astype(int), 0, ih - 1)
            arr = np.asarray(img)
            out = arr[py, px]
            return out
    if visual.kind == "vertex" and visual.vertex_colors is not None:
        pts, _, tri_ids = mesh.nearest.on_surface(centers)
        cols = np.asarray(visual.vertex_colors, dtype=np.uint8)
        out = cols[mesh.faces[tri_ids][:, 0]][:, :3]
    return out


def voxelize_solid(mesh: trimesh.Trimesh, pitch: float):
    """自研实心体素化：三角形边采样标记表面 → 洪水填充内部。
    对非水密 AI 网格比 trimesh 的 subdivide（丢细长凸起如弹匣）可靠。"""
    mn = mesh.bounds[0]
    mx = mesh.bounds[1]
    shape = tuple((np.ceil((mx - mn) / pitch).astype(int) + 1).tolist())
    origin = mn - np.array([pitch / 2.0] * 3)
    transform = np.eye(4)
    transform[:3, :3] *= pitch
    transform[:3, 3] = origin

    def to_idx(p: np.ndarray) -> np.ndarray:
        return np.floor((p - origin) / pitch).astype(np.int64)

    surf = np.zeros(shape, dtype=bool)
    verts = mesh.vertices
    tris = mesh.faces
    samples = []
    for t in tris:
        a, b, c = verts[t]
        # 重心网格采样：边长按 pitch/2 细分，保证每个体素被表面覆盖
        max_edge = max(
            np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        )
        s = max(1, int(np.ceil(max_edge / (pitch * 0.5))))
        for u_i in range(s + 1):
            for v_i in range(s + 1 - u_i):
                u = u_i / s
                v = v_i / s
                samples.append(a + (b - a) * u + (c - a) * v)
    S = np.asarray(samples)
    idx = to_idx(S)
    ok = (
        (idx[:, 0] >= 0) & (idx[:, 0] < shape[0])
        & (idx[:, 1] >= 0) & (idx[:, 1] < shape[1])
        & (idx[:, 2] >= 0) & (idx[:, 2] < shape[2])
    )
    surf[idx[ok, 0], idx[ok, 1], idx[ok, 2]] = True

    # 洪水填充：从边界找外部可达的空格
    exterior = np.zeros(shape, dtype=bool)
    stack = []
    for i in range(shape[0]):
        for k in range(shape[2]):
            for j in [0, shape[1] - 1]:
                if not surf[i, j, k]:
                    exterior[i, j, k] = True
                    stack.append((i, j, k))
    for j in range(shape[1]):
        for k in range(shape[2]):
            for i in [0, shape[0] - 1]:
                if not surf[i, j, k]:
                    exterior[i, j, k] = True
                    stack.append((i, j, k))
    for i in range(shape[0]):
        for j in range(shape[1]):
            for k in [0, shape[2] - 1]:
                if not surf[i, j, k]:
                    exterior[i, j, k] = True
                    stack.append((i, j, k))
    while stack:
        i, j, k = stack.pop()
        for di, dj, dk in [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]:
            ni, nj, nk = i + di, j + dj, k + dk
            if (
                0 <= ni < shape[0]
                and 0 <= nj < shape[1]
                and 0 <= nk < shape[2]
                and not surf[ni, nj, nk]
                and not exterior[ni, nj, nk]
            ):
                exterior[ni, nj, nk] = True
                stack.append((ni, nj, nk))

    filled = surf | ~exterior
    grid = trimesh.voxel.VoxelGrid(filled, transform=transform)
    return grid, surf


def quantize_palette(colors: np.ndarray, max_colors: int) -> tuple:
    """颜色量化到调色板，返回 (索引数组, 调色板 RGB)。"""
    img = Image.fromarray(colors.reshape(-1, 1, 3).repeat(1, axis=1), "RGB")
    q = img.quantize(colors=min(max_colors, 256), method=Image.MEDIANCUT)
    pal = q.getpalette()[: 256 * 3]
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal)
    idx = np.asarray(q.convert("RGB")).reshape(-1, 3)
    pal_rgb = np.array(pal).reshape(-1, 3)
    # 把量化后每个体素的颜色映射回最近的调色板索引
    diff = ((idx[:, None, :].astype(int) - pal_rgb[None, :, :].astype(int)) ** 2).sum(axis=2)
    indices = diff.argmin(axis=1).astype(np.uint8) + 1
    return indices, pal_rgb


def split_magazine(
    filled: np.ndarray,
    z_threshold: int = 18,
    bottom_margin: int = 28,
    mag_height: int = 25,
    x_lo: float = 0.30,
    x_hi: float = 0.52,
) -> tuple:
    """把悬挂在机匣下方的弹匣拆成独立体素。
    弹匣列 = 底部低于机匣地板（全局最低 + bottom_margin）的列；
    弹匣顶 = 该列 z 宽度 <= 阈值的最高的连续行（上方变宽=进入机匣）。
    阈值需介于弹匣宽与机匣宽之间（实测弹匣 zw≈15、机匣 zw≈22 → 取 18）。"""
    shape = filled.shape
    jmin = np.full((shape[0], shape[2]), shape[1])
    for i in range(shape[0]):
        for k in range(shape[2]):
            js = np.nonzero(filled[i, :, k])[0]
            if js.size:
                jmin[i, k] = js[0]
    bottom = int(jmin.min())
    mag = np.zeros_like(filled)
    for i in range(shape[0]):
        for k in range(shape[2]):
            # 弹匣只在枪身中前段（x 比例限制），防止吞入护木/枪管
            if not (x_lo * shape[0] <= i <= x_hi * shape[0]):
                continue
            if jmin[i, k] > bottom + bottom_margin:
                continue
            top_j = -1
            for j in range(shape[1]):
                zw = int(filled[i, j, :].sum())
                if zw > 0:
                    if zw <= z_threshold:
                        top_j = j
                    else:
                        break
            # 弹匣高度上限：列底 + mag_height 格（0.125m），防止弹匣井/护木窄段被吞入
            if top_j >= 0:
                top_j = min(top_j, jmin[i, k] + mag_height)
            if top_j >= 0:
                mag[i, : top_j + 1, k] = filled[i, : top_j + 1, k]
    return filled & ~mag, mag


def extract_surface(filled: np.ndarray) -> np.ndarray:
    """提取表面体素（至少一个 6 邻域为空）。"""
    if filled.ndim != 3 or filled.shape[0] < 3:
        return filled.copy()
    pad = np.pad(filled, 1)
    out = np.zeros_like(filled)
    for di, dj, dk in [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]:
        out |= filled & ~pad[
            1 + di : 1 + di + filled.shape[0],
            1 + dj : 1 + dj + filled.shape[1],
            1 + dk : 1 + dk + filled.shape[2],
        ]
    return out


def write_vox(path: str, shape: tuple, indices: np.ndarray, palette: np.ndarray) -> None:
    sx, sy, sz = (int(s) for s in shape)
    xs, ys, zs = np.nonzero(indices > 0)
    n = len(xs)
    body = struct.pack("<III", sx, sy, sz)
    body += struct.pack("<I", n)
    for x, y, z, c in zip(xs, ys, zs, indices[xs, ys, zs]):
        body += struct.pack("<BBBB", int(x), int(y), int(z), int(c))
    # RGBA 调色板（256 项，索引 0 保留）
    pal = np.zeros((256, 4), dtype=np.uint8)
    cnt = min(len(palette), 255)
    pal[1 : cnt + 1, :3] = palette[:cnt]
    for i in range(1, 256):
        pal[i, 3] = 255
    body += pal.tobytes()
    chunks = b""
    chunks += b"SIZE" + struct.pack("<II", 12, 0) + struct.pack("<III", sx, sy, sz)
    chunks += b"XYZI" + struct.pack("<II", 4 + n * 4, 0) + body[12 : 12 + 4 + n * 4]
    chunks += b"RGBA" + struct.pack("<II", 1024, 0) + body[12 + 4 + n * 4 :]
    with open(path, "wb") as f:
        f.write(b"VOX ")
        f.write(struct.pack("<I", 150))
        f.write(b"MAIN" + struct.pack("<II", 0, len(chunks)))
        f.write(chunks)
    print("vox:", path, "shape", shape, "filled", n, "palette", cnt)


def write_obj_with_colors(path: str, shape: tuple, indices: np.ndarray, palette: np.ndarray, pitch: float) -> None:
    """每个体素生成一个带顶点色的方盒（12 三角面）。"""
    xs, ys, zs = np.nonzero(indices > 0)
    n = len(xs)
    with open(path, "w") as f:
        f.write("# voxelized gun (vertex colors)\n")
        # 体素单位边长 1，中心在 (x+0.5, y+0.5, z+0.5)
        corners = np.array(
            [
                [0, 0, 0],
                [1, 0, 0],
                [1, 1, 0],
                [0, 1, 0],
                [0, 0, 1],
                [1, 0, 1],
                [1, 1, 1],
                [0, 1, 1],
            ],
            dtype=float,
        )
        faces = np.array(
            [
                [1, 0, 3, 2],  # 底面 z=0，法线 -Z
                [4, 5, 6, 7],  # 顶面 z=1，法线 +Z
                [0, 1, 5, 4],  # 前面 y=0，法线 -Y
                [2, 3, 7, 6],  # 后面 y=1，法线 +Y
                [3, 0, 4, 7],  # 左面 x=0，法线 -X
                [1, 2, 6, 5],  # 右面 x=1，法线 +X
            ],
            dtype=int,
        )
        base = 1
        half = np.array(shape, dtype=float) / 2.0
        for x, y, z, c in zip(xs, ys, zs, indices[xs, ys, zs]):
            r, g, b = palette[int(c) - 1]
            # 居中：体素中心 = (x+0.5)*pitch，整体平移使模型中心落在原点（与 GLB 一致）
            for cx, cy, cz in ((corners + np.array([x, y, z]) + 0.5 - half) * pitch):
                # Godot/MagicaVoxel 读 OBJ 顶点色为 0..1 浮点
                f.write("v %.6f %.6f %.6f %.4f %.4f %.4f\n" % (cx, cy, cz, r / 255.0, g / 255.0, b / 255.0))
            for quad in faces:
                f.write("f %d %d %d %d\n" % tuple(base + quad))
            base += 8
    print("obj:", path, "voxels", n)


def main() -> int:
    ap = argparse.ArgumentParser(description="GLB → 高精度体素 (.vox + 顶点色 OBJ)")
    ap.add_argument("--input", required=True, help="GLB 路径")
    ap.add_argument("--pitch", type=float, default=0.005, help="体素边长（米），默认 0.005=0.5cm")
    ap.add_argument("--out", default=None, help="输出路径前缀（默认与输入同名）")
    ap.add_argument("--palette", type=int, default=96, help="调色板最大颜色数，默认 96")
    args = ap.parse_args()

    base = args.out or os.path.splitext(args.input)[0]
    t_start = time.time()
    mesh = load_single_mesh(args.input)
    print("mesh:", len(mesh.vertices), "verts,", len(mesh.faces), "faces")
    print("stage load %.2fs" % (time.time() - t_start))
    vox, surf = voxelize_solid(mesh, args.pitch)
    print("stage voxelize %.2fs" % (time.time() - t_start))
    shape = tuple(int(s) for s in vox.shape)
    filled = np.asarray(vox.matrix, dtype=bool)
    print("stage solid %.2fs surface=%d solid=%d" % (time.time() - t_start, int(surf.sum()), int(filled.sum())))
    if max(shape) > 255:
        print("警告：体素网格超过 255 格，MagicaVoxel 标准世界放不下；请加大 pitch")
    idx = np.array(np.nonzero(filled))
    centers = (vox.transform @ np.vstack([idx + 0.5, np.ones(idx.shape[1])]))[:3].T
    print("stage centers %.2fs n=%d" % (time.time() - t_start, len(centers)))
    colors = sample_colors(mesh, centers)
    print("stage colors %.2fs unique=%d" % (time.time() - t_start, len(np.unique(colors, axis=0))))
    indices, palette = quantize_palette(colors, args.palette)
    print("stage palette %.2fs" % (time.time() - t_start))
    grid = np.zeros(shape, dtype=np.uint8)
    idx3 = tuple(np.nonzero(filled))
    grid[idx3] = indices
    # 弹匣拆分：枪体 + 独立弹匣（换弹动画滑出用）
    body, mag_v = split_magazine(filled)
    print("stage split %.2fs body=%d mag=%d" % (time.time() - t_start, int(body.sum()), int(mag_v.sum())))
    # .vox 只含枪体（无弹匣）；弹匣单独出 .vox
    body_grid = np.zeros(shape, dtype=np.uint8)
    body_idx = np.nonzero(body)
    body_grid[body_idx] = grid[body_idx]
    mag_grid = np.zeros(shape, dtype=np.uint8)
    mag_idx = np.nonzero(mag_v)
    mag_grid[mag_idx] = grid[mag_idx]
    write_vox(base + ".vox", shape, body_grid, palette)
    write_vox(base + "_mag.vox", shape, mag_grid, palette)
    print("stage vox %.2fs" % (time.time() - t_start))
    for name, part in [("", body), ("_mag", mag_v)]:
        part_surf = extract_surface(part)
        part_grid = np.zeros(shape, dtype=np.uint8)
        part_idx = np.nonzero(part_surf)
        part_grid[part_idx] = grid[part_idx]
        write_obj_with_colors(base + name + ".obj", shape, part_grid, palette, args.pitch)
    print("stage obj %.2fs" % (time.time() - t_start))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
