#!/usr/bin/env python3
"""从源 GLB 中删除弹匣三角面，生成“无弹匣枪体”GLB。

弹匣识别（与 voxelize_glb.split_magazine 同口径）：
  - x 在枪体中前段（x_lo~x_hi 比例，AK 为 0.30~0.52 → 原始坐标 -0.165..0.0）
  - 质心 y 低于机匣地板（y_floor=-0.10）

用法：
  python strip_mag_glb.py --input assets/models/akm_trellis.glb --out assets/models/akm_trellis_nomag.glb
"""

import argparse

import numpy as np
import trimesh


def strip_mag(mesh: trimesh.Trimesh, x_lo: float = 0.30, x_hi: float = 0.495, y_floor: float = -0.05) -> trimesh.Trimesh:
    mn = mesh.bounds[0]
    extent = mesh.bounds[1] - mesh.bounds[0]
    xa = mn[0] + extent[0] * x_lo
    xb = mn[0] + extent[0] * x_hi
    keep = np.ones(len(mesh.faces), dtype=bool)
    tris = mesh.faces
    for i, t in enumerate(tris):
        # 任一顶点落在弹匣盒（x 中前段 + y 低于机匣地板）内即删除该面
        verts = mesh.vertices[t]
        if ((verts[:, 0] >= xa) & (verts[:, 0] <= xb) & (verts[:, 1] < y_floor)).any():
            keep[i] = False
    removed = int((~keep).sum())
    mesh.update_faces(keep)
    mesh.remove_unreferenced_vertices()
    print("移除弹匣三角面:", removed, " 剩余:", len(mesh.faces))
    return mesh


def main() -> int:
    ap = argparse.ArgumentParser(description="删除 GLB 中的弹匣")
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--y-floor", type=float, default=-0.05)
    ap.add_argument("--x-lo", type=float, default=0.30)
    ap.add_argument("--x-hi", type=float, default=0.495)
    args = ap.parse_args()
    scene = trimesh.load(args.input, force="scene")
    mesh = scene.to_geometry()
    mesh = strip_mag(mesh, args.x_lo, args.x_hi, args.y_floor)
    mesh.export(args.out)
    print("导出:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
