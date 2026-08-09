#!/usr/bin/env python3
"""Sketchfab AKM.obj 预处理：剔道具 → 转正(Z→X) → 矫正倾斜 → 归一化1m。

两种输出模式：
- 贴图模式（--mtl + --tex-dir）：保留 UV，写 MTL 引用 PBR 贴图，Godot 导入带材质
- 顶点色模式（默认）：按部位上色（无贴图时的兜底）

用法：
  python tools/ai-gen/prep_akm_obj.py --input assets/models/ak/akm_sketchfab.obj \
      --out assets/models/ak/akm_sketchfab_prep.obj --mtl assets/models/ak/akm_sketchfab_prep.mtl \
      --tex-dir assets/models/ak/akm_sketchfab_tex
"""

import argparse
import numpy as np

WOOD = (150.0 / 255, 95.0 / 255, 45.0 / 255)
WOOD_DARK = (112.0 / 255, 70.0 / 255, 38.0 / 255)
STEEL = (92.0 / 255, 94.0 / 255, 99.0 / 255)
STEEL_DARK = (52.0 / 255, 53.0 / 255, 57.0 / 255)
MAG_COLOR = (66.0 / 255, 68.0 / 255, 72.0 / 255)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mtl", default=None, help="输出 MTL 路径（贴图模式）")
    ap.add_argument("--tex-dir", default=None, help="贴图目录（相对项目根，写进 MTL）")
    args = ap.parse_args()

    # 1. 解析 OBJ（按 usemtl 分组）
    verts = []
    normals = []
    uvs = []
    faces = []  # (mat_idx, [(v_idx, vt_idx), ...])
    mat_of = {}
    mat_names = []
    cur = None
    with open(args.input, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                p = line.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("vn "):
                p = line.split()
                normals.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("vt "):
                p = line.split()
                uvs.append((float(p[1]), float(p[2])))
            elif line.startswith("usemtl"):
                name = line.split()[1]
                if name not in mat_of:
                    mat_of[name] = len(mat_names)
                    mat_names.append(name)
                cur = mat_of[name]
            elif line.startswith("f "):
                idxs = []
                for tok in line.split()[1:]:
                    parts = tok.split("/")
                    v_i = int(parts[0]) - 1
                    vt_i = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1
                    idxs.append((v_i, vt_i))
                faces.append((cur if cur is not None else 0, idxs))
    V = np.array(verts)
    N = np.array(normals) if normals else np.zeros_like(V)
    print("materials:", mat_names, "verts", len(V), "faces", len(faces))

    # 2. 剔除独立道具（bullet 组）：保留与最大组 AABB 相交的组
    group_verts = {}
    for mi, name in enumerate(mat_names):
        idxs = set()
        for m, fidxs in faces:
            if m == mi:
                idxs.update(v_i for v_i, _ in fidxs)
        group_verts[name] = np.array(sorted(idxs))
    sizes = {name: len(idx) for name, idx in group_verts.items()}
    main_name = max(sizes, key=sizes.get)
    keep = set()
    main_aabb = V[group_verts[main_name]]
    lo0, hi0 = main_aabb.min(0), main_aabb.max(0)
    for name, idx in group_verts.items():
        a = V[idx]
        lo, hi = a.min(0), a.max(0)
        if (lo <= hi0 + 0.05).all() and (hi >= lo0 - 0.05).all():
            keep.add(name)
    print("keep groups:", sorted(keep), " drop:", sorted(set(mat_names) - keep))
    keep_idx = set()
    for name in keep:
        keep_idx.update(group_verts[name].tolist())

    # 3. 变换：Z→X（绕Y -90°），再绕新 Z 轴矫正 y-x 倾斜
    V2 = np.stack([V[:, 2], V[:, 1], -V[:, 0]], axis=1)
    N2 = np.stack([N[:, 2], N[:, 1], -N[:, 0]], axis=1)
    akm_idx = group_verts.get("akm", group_verts[main_name])
    xf = V2[akm_idx]
    slope = float(np.polyfit(xf[:, 0], xf[:, 1], 1)[0])
    theta = -np.arctan(slope)
    c, s = np.cos(theta), np.sin(theta)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)
    V3 = V2 @ R.T
    N3 = N2 @ R.T
    print("tilt deg:", round(float(np.degrees(theta)), 2))

    # 4. 居中 + 归一化到枪长 1.0m（X 轴），保证 gun.gd 缩放落在合理区间
    lo, hi = V3.min(0), V3.max(0)
    center = (lo + hi) / 2.0
    length = hi[0] - lo[0]
    scale = 1.0 / length if length > 0 else 1.0
    V4 = (V3 - center) * scale
    N4 = N3  # 旋转保持长度，无需缩放
    print("normalized length:", round(float(length * scale), 3), "aabb:", [round(x, 3) for x in (V4.min(0))], [round(x, 3) for x in (V4.max(0))])

    # 5. 判断枪口端：细端 = 枪口（平均离轴半径小）
    x = V4[:, 0]
    span = x.max() - x.min()
    ends = {}
    for end, sel in (("-X", x < x.min() + span * 0.08), ("+X", x > x.max() - span * 0.08)):
        sel_idx = np.nonzero(sel)[0]
        if len(sel_idx):
            r = np.sqrt(V4[sel_idx, 1] ** 2 + V4[sel_idx, 2] ** 2).mean()
            ends[end] = r
    print("end radii:", {k: round(float(v), 3) for k, v in ends.items()})
    muzzle_plus = ends.get("+X", 1.0) < ends.get("-X", 1.0)
    print("muzzle at +X:", muzzle_plus)
    if not muzzle_plus:
        V4[:, 0] = -V4[:, 0]
        N4[:, 0] = -N4[:, 0]

    # 6-7. 写出 OBJ
    with open(args.out, "w", encoding="utf-8") as f:
        if args.mtl:
            f.write("# akm sketchfab prep (PBR mtl, X-axis, muzzle +X)\n")
            f.write("mtllib %s\n" % args.mtl.split("/")[-1])
            for i in range(len(V)):
                v = V4[i]
                f.write("v %.6f %.6f %.6f\n" % (v[0], v[1], v[2]))
            for u in uvs:
                f.write("vt %.6f %.6f\n" % (u[0], 1.0 - u[1]))
            last_mi = None
            for mi, fidxs in faces:
                if mat_names[mi] not in keep:
                    continue
                if mi != last_mi:
                    f.write("usemtl %s\n" % mat_names[mi])
                    last_mi = mi
                f.write(
                    "f "
                    + " ".join(
                        "%d/%d" % (v_i + 1, (vt_i + 1) if vt_i >= 0 else (v_i + 1))
                        for v_i, vt_i in fidxs
                    )
                    + "\n"
                )
        else:
            f.write("# akm sketchfab prep (vertex colors, X-axis, muzzle +X)\n")
            colors = np.zeros((len(V), 3), dtype=float)
            for mi, fidxs in faces:
                name = mat_names[mi]
                if name not in keep:
                    continue
                c = V4[[v_i for v_i, _ in fidxs]].mean(axis=0)
                if name == "magazine":
                    col = MAG_COLOR
                elif c[0] < -0.23:  # 枪托
                    col = WOOD
                elif 0.12 < c[0] < 0.30:  # 护木
                    col = WOOD
                elif -0.22 < c[0] < -0.03 and c[1] < -0.008:  # 握把
                    col = WOOD_DARK
                elif 0.28 < c[0] and c[1] > 0.03:  # 准星/枪口上部
                    col = STEEL_DARK
                else:
                    col = STEEL
                for v_i, _ in fidxs:
                    colors[v_i] = col
            for i in range(len(V)):
                v = V4[i]
                col = colors[i]
                f.write("v %.6f %.6f %.6f %.4f %.4f %.4f\n" % (v[0], v[1], v[2], col[0], col[1], col[2]))
            for mi, fidxs in faces:
                if mat_names[mi] not in keep:
                    continue
                f.write("f " + " ".join(str(v_i + 1) for v_i, _ in fidxs) + "\n")
    print("written:", args.out)

    if args.mtl:
        tex = args.tex_dir or "."
        with open(args.mtl, "w", encoding="utf-8") as f:
            for mat, pre in (("akm", "akm"), ("magazine", "mag")):
                f.write("newmtl %s\n" % mat)
                f.write("Kd 1 1 1\nKs 0.1 0.1 0.1\nNs 64\n")
                f.write("map_Kd %s/%s_basecolor.png\n" % (tex, pre))
                f.write("map_Bump %s/%s_normal.png\n" % (tex, pre))
                f.write("map_Pm %s/%s_metallic.png\n" % (tex, pre))
                f.write("map_Ps %s/%s_roughness.png\n" % (tex, pre))
                f.write("map_Ka %s/%s_ao.png\n" % (tex, pre))
        print("written:", args.mtl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
