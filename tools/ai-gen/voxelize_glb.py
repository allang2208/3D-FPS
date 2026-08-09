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
        for x, y, z, c in zip(xs, ys, zs, indices[xs, ys, zs]):
            r, g, b = palette[int(c) - 1]
            for cx, cy, cz in (corners + np.array([x, y, z])) * pitch:
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
    vox = mesh.voxelized(pitch=args.pitch)
    print("stage voxelize %.2fs" % (time.time() - t_start))
    shape = tuple(int(s) for s in vox.shape)
    if max(shape) > 255:
        print("警告：体素网格超过 255 格，MagicaVoxel 标准世界放不下；请加大 pitch")
    idx = np.array(np.nonzero(vox.matrix > 0))
    centers = (vox.transform @ np.vstack([idx + 0.5, np.ones(idx.shape[1])]))[:3].T
    print("stage centers %.2fs n=%d" % (time.time() - t_start, len(centers)))
    colors = sample_colors(mesh, centers)
    print("stage colors %.2fs unique=%d" % (time.time() - t_start, len(np.unique(colors, axis=0))))
    indices, palette = quantize_palette(colors, args.palette)
    print("stage palette %.2fs" % (time.time() - t_start))
    grid = np.zeros(shape, dtype=np.uint8)
    idx3 = tuple(np.nonzero(vox.matrix > 0))
    grid[idx3] = indices
    vox_path = base + ".vox"
    obj_path = base + ".obj"
    write_vox(vox_path, shape, grid, palette)
    print("stage vox %.2fs" % (time.time() - t_start))
    write_obj_with_colors(obj_path, shape, grid, palette, args.pitch)
    print("stage obj %.2fs" % (time.time() - t_start))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
