#!/usr/bin/env python3
"""One-shot: orthogonalize Terrain3D normal maps for detiling compatibility.

Terrain3D's channel packer warns that normal maps must be orthogonal to the
UV plane (average normal ~ (0,0,1)) before enabling detiling rotation;
otherwise the rotated tiles produce a reflective checkerboard / hazy look.
This re-aligns every *_nrm_rgh.png in terrain_prepared using the same
rotation-basis math as addons/terrain_3d/menu/channel_packer.gd
(_alignment_basis + _align_normals), preserving the roughness alpha.

Usage: python tools/orthogonalize_terrain_normals.py
"""

import os

import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..", "assets", "textures", "terrain_prepared")


def alignment_basis(normal):
    """Basis whose rows match Terrain3D's _alignment_basis; Godot `v * B`
    (== B^T applied) maps the map-average normal onto +Z."""
    up = np.array([0.0, 0.0, 1.0])
    v = np.cross(normal, up)
    c = float(np.dot(normal, up))
    k = 1.0 / (1.0 + c)
    vxy = v[0] * v[1] * k
    vxz = v[0] * v[2] * k
    vyz = v[1] * v[2] * k
    return np.array([
        [v[0] * v[0] * k + c, vxy - v[2], vxz + v[1]],
        [vxy + v[2], v[1] * v[1] * k + c, vyz - v[0]],
        [vxz - v[1], vyz + v[0], v[2] * v[2] * k + c],
    ])


def main():
    files = sorted(f for f in os.listdir(ROOT) if f.endswith("_nrm_rgh.png"))
    for name in files:
        path = os.path.join(ROOT, name)
        img = Image.open(path).convert("RGBA")
        arr = np.asarray(img, dtype=np.float32) / 255.0
        rgb = arr[..., :3]
        alpha = arr[..., 3]
        normals = rgb * 2.0 - 1.0
        avg = normals.reshape(-1, 3).mean(axis=0)
        avg_n = avg / np.linalg.norm(avg)
        if avg_n[2] >= 0.999:
            print(f"{name}: aligned (z={avg_n[2]:.4f}), skip")
            continue
        basis = alignment_basis(avg_n)
        out = (basis.T @ normals.reshape(-1, 3).T).T
        out = out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-6)
        out = (out + 1.0) * 0.5
        out = np.clip(out, 0.0, 1.0)
        new_arr = np.dstack([out.reshape(arr.shape[:2] + (3,)), alpha])
        new_img = Image.fromarray((new_arr * 255.0).round().astype(np.uint8), "RGBA")
        new_img.save(path)
        new_avg = (out.mean(axis=0) * 2.0 - 1.0)
        print(f"{name}: z {avg_n[2]:.4f} -> {new_avg[2]:.4f} (aligned)")


if __name__ == "__main__":
    main()
