#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TACZ / Bedrock geometry + animation -> skinned GLB converter.

Reads Minecraft Bedrock-style geometry JSON (format_version 1.12.0,
geo_models/*.json) and Bedrock animation JSON (format_version 1.8.0),
and writes a glTF 2.0 binary (.glb) with a skeleton and animations.

Conventions implemented (verified against Blockbench source):
  - Cube origins/pivots are absolute model-space coordinates.
  - A bone transform is T(pivot) * R * S * T(-pivot); at rest the node
    TRS is T(pivot - R*S*pivot, R, S) so bind matrices are identity.
  - Per-face UV: {"uv":[u,v], "uv_size":[us,vs]}; u/v are texture pixels
    with top-left origin.  Negative uv_size mirrors the face.
  - Face winding from Blockbench CubeFace.getVertexIndices, reversed so
    glTF normals point outward.
  - Legacy box UV (plain "uv":[u,v]) uses the standard Java/blockbench
    box layout.
  - Animations: position/rotation/scale channels; keyframes may be plain
    arrays, {time: array} maps, or {"pre":..,"post":..} with lerp_mode
    (catmullrom/step).  Rotation channels are re-sampled to linear quat
    keyframes to avoid slerp wrap-around.

Optional --split-bone writes a second static (unskinned) GLB containing
only the cubes of that bone subtree, for detachable magazines etc.

Usage:
  python tools/ai-gen/tacz_geo_to_glb.py \
    --geo <geo.json> --anim <animation.json> \
    --texture <albedo.png> [--normal <n.png>] \
    --out <out.glb> [--split-bone magazine --out-mag <mag.glb>]
"""

import argparse
import json
import math
import os
import struct
import sys

# --------------------------------------------------------------------------
# Face tables (Blockbench CubeFace.getVertexIndices + UV corner mapping)
# --------------------------------------------------------------------------

# corner index -> (x,y,z) offsets from cube origin in +size direction
CORNERS = {
    # from Blockbench getGlobalVertexPositions: 0..7
    0: (1, 1, 1),  # toX, toY, toZ
    1: (1, 1, 0),  # toX, toY, fromZ
    2: (1, 0, 1),  # toX, fromY, toZ
    3: (1, 0, 0),  # toX, fromY, fromZ
    4: (0, 1, 0),  # fromX, toY, fromZ
    5: (0, 1, 1),  # fromX, toY, toZ
    6: (0, 0, 0),  # fromX, fromY, fromZ
    7: (0, 0, 1),  # fromX, fromY, toZ
}

# face name -> ordered list of (corner_index, uv_role)
# role 'tl' = (u0, v0), 'tr' = (u2, v0), 'bl' = (u0, v2), 'br' = (u2, v2)
# order is CCW seen from outside (reversed Blockbench winding)
FACES = {
    "north": [(1, "tl"), (3, "bl"), (6, "br"), (4, "tr")],
    "east":  [(0, "tl"), (2, "bl"), (3, "br"), (1, "tr")],
    "south": [(5, "tl"), (7, "bl"), (2, "br"), (0, "tr")],
    "west":  [(4, "tl"), (6, "bl"), (7, "br"), (5, "tr")],
    "up":    [(4, "tl"), (5, "bl"), (0, "br"), (1, "tr")],
    "down":  [(7, "tl"), (6, "bl"), (3, "br"), (2, "tr")],
}

UV_ROLE = {"tl": (0, 0), "tr": (1, 0), "bl": (0, 1), "br": (1, 1)}


def euler_quat(x_deg, y_deg, z_deg, order="XYZ"):
    """XYZ-order intrinsic Euler degrees -> quaternion (w,x,y,z)."""
    x = math.radians(x_deg)
    y = math.radians(y_deg)
    z = math.radians(z_deg)
    # intrinsic XYZ == extrinsic ZYX: q = qz * qy * qx
    cx, sx = math.cos(x / 2), math.sin(x / 2)
    cy, sy = math.cos(y / 2), math.sin(y / 2)
    cz, sz = math.cos(z / 2), math.sin(z / 2)
    if order == "XYZ":
        w = cx * cy * cz + sx * sy * sz
        qx = sx * cy * cz - cx * sy * sz
        qy = cx * sy * cz + sx * cy * sz
        qz = cx * cy * sz - sx * sy * cz
    elif order == "ZYX":
        # intrinsic ZYX == extrinsic XYZ: q = qx * qy * qz
        w = cx * cy * cz + sx * sy * sz
        qx = sx * cy * cz
        qy = cx * sy * cz
        qz = cx * cy * sz
    else:
        raise ValueError(f"unsupported euler order {order}")
    return (w, qx, qy, qz)


def quat_mul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def quat_conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def quat_rot_vec(q, v):
    qv = (0.0, v[0], v[1], v[2])
    r = quat_mul(quat_mul(q, qv), quat_conj(q))
    return (r[1], r[2], r[3])


def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def v_len(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def v_lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def v_rot_euler(v, pivot, euler_deg, order="XYZ"):
    """Rotate v about pivot by euler degrees (XYZ intrinsic)."""
    rel = v_sub(v, pivot)
    q = euler_quat(*euler_deg, order)
    rot = quat_rot_vec(q, rel)
    return v_add(pivot, rot)


def v_rot_matrix(euler_deg, order="XYZ"):
    """Rotation matrix (row-major 3x3) from euler degrees."""
    q = euler_quat(*euler_deg, order)
    w, x, y, z = q
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def mat_mul_vec(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


# --------------------------------------------------------------------------
# Geometry parsing
# --------------------------------------------------------------------------


def parse_geometry(geo_path):
    with open(geo_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    geo = data["minecraft:geometry"][0]
    desc = geo.get("description", {})
    tex_w = desc.get("texture_width", 64)
    tex_h = desc.get("texture_height", 64)
    bones_raw = geo.get("bones", [])

    bones = []
    by_name = {}
    for b in bones_raw:
        entry = {
            "name": b.get("name", ""),
            "parent": b.get("parent", None),
            "pivot": tuple(b.get("pivot", [0.0, 0.0, 0.0])),
            "rotation": tuple(b.get("rotation", [0.0, 0.0, 0.0])),
            "mirror": b.get("mirror", False),
            "cubes": [],
        }
        for c in b.get("cubes", []):
            origin = tuple(c.get("origin", [0.0, 0.0, 0.0]))
            size = tuple(c.get("size", [1.0, 1.0, 1.0]))
            inflate = c.get("inflate", 0.0)
            cpivot = tuple(c.get("pivot", [0.0, 0.0, 0.0]))
            crot = tuple(c.get("rotation", [0.0, 0.0, 0.0]))
            uv = c.get("uv", [0.0, 0.0])
            entry["cubes"].append({
                "origin": origin,
                "size": size,
                "inflate": inflate,
                "pivot": cpivot,
                "rotation": crot,
                "uv": uv,
            })
        bones.append(entry)
        by_name[entry["name"]] = entry

    # topological order: parents before children
    ordered = []
    visited = set()

    def visit(b):
        if b["name"] in visited:
            return
        visited.add(b["name"])
        if b["parent"] and b["parent"] in by_name:
            visit(by_name[b["parent"]])
        ordered.append(b)

    for b in bones:
        visit(b)

    # root bones (no parent) -> also include any parentless bones
    roots = [b for b in ordered if not b["parent"]]
    return ordered, roots, tex_w, tex_h


# --------------------------------------------------------------------------
# Animation parsing / sampling
# --------------------------------------------------------------------------


def norm_keyframes(raw):
    """Normalize a bedrock channel value to [(time, value)]."""
    if isinstance(raw, (list, tuple)):
        return [(0.0, tuple(float(x) if isinstance(x, (int, float)) else 0.0
                            for x in raw))]
    if isinstance(raw, dict):
        if "pre" in raw or "post" in raw:
            # {pre, post, lerp_mode} -> value = post (start of this keyframe)
            v = raw.get("post", raw.get("pre", [0.0, 0.0, 0.0]))
            return [(0.0, tuple(float(x) if isinstance(x, (int, float)) else 0.0
                                for x in v))]
        out = []
        for t, v in sorted(raw.items()):
            if t in ("lerp_mode",):
                continue
            try:
                ft = float(t)
            except (TypeError, ValueError):
                continue
            if isinstance(v, (list, tuple)):
                out.append((ft, tuple(
                    float(x) if isinstance(x, (int, float)) else 0.0 for x in v)))
            elif isinstance(v, dict):
                vv = v.get("post", v.get("pre", [0.0, 0.0, 0.0]))
                out.append((ft, tuple(
                    float(x) if isinstance(x, (int, float)) else 0.0 for x in vv)))
        return out
    return []


def get_lerp_mode(raw, default="linear"):
    if isinstance(raw, dict):
        mode = raw.get("lerp_mode")
        if mode:
            return mode
        # per-keyframe dict: check nested values
        for v in raw.values():
            if isinstance(v, dict) and v.get("lerp_mode"):
                return v["lerp_mode"]
    return default


def catmullrom(points, t, alpha=0.5):
    """Centripetal Catmull-Rom through 4 points (each (time, vec))."""
    p0, p1, p2, p3 = points
    t0, t1, t2, t3 = (p[0] for p in points)
    if t1 == t2:
        return p1[1]
    eps = 1e-9
    d1 = max(abs(t1 - t0), eps) ** alpha
    d2 = max(abs(t2 - t1), eps) ** alpha
    d3 = max(abs(t3 - t2), eps) ** alpha
    u0, u1, u2, u3 = 0.0, d1, d1 + d2, d1 + d2 + d3
    u = u1 + (u2 - u1) * ((t - t1) / (t2 - t1)) if t2 != t1 else u1

    def a(p_a, p_b, ui, uj):
        return tuple((p_b[k] - p_a[k]) / (uj - ui) for k in range(3)) if uj != ui else (0.0, 0.0, 0.0)

    a1 = a(p0[1], p1[1], u0, u1)
    a2 = a(p1[1], p2[1], u1, u2)
    a3 = a(p2[1], p3[1], u2, u3)
    b1 = tuple((u2 - u1) * x for x in a1)
    b2 = tuple((u1 - u0) * x for x in a2)
    c1 = tuple((u2 - u1) * x for x in a2)
    c2 = tuple((u3 - u2) * x for x in a3)
    p = tuple(
        ((u2 - u) / (u2 - u1)) * p1[1][k]
        + ((u - u1) / (u2 - u1)) * p2[1][k]
        + ((u2 - u) * (u - u1) / (u2 - u1) ** 2) * (b1[k] - b2[k])
        + ((u2 - u) * (u - u1) / (u2 - u1) ** 2) * (c1[k] - c2[k])
        for k in range(3)
    )
    return p


def sample_channel(raw_kfs, length, channel, samples_per_seg=12):
    """
    Return a list of (time, value) samples for glTF linear interpolation.
    channel in {'rotation','translation','scale'}.
    """
    pts = sorted(norm_keyframes(raw_kfs))
    if not pts:
        return []
    if len(pts) == 1:
        return [(0.0, pts[0][1])]

    # collect lerp mode for each destination keyframe
    modes = {}
    if isinstance(raw_kfs, dict):
        for t, v in raw_kfs.items():
            if t == "lerp_mode":
                continue
            try:
                ft = float(t)
            except (TypeError, ValueError):
                continue
            if isinstance(v, dict):
                modes[ft] = v.get("lerp_mode", "linear")

    out = [pts[0]]
    for i in range(len(pts) - 1):
        t0, v0 = pts[i]
        t1, v1 = pts[i + 1]
        mode = modes.get(t1, "linear")
        if mode == "step":
            out.append((t1, v0))
            out.append((t1, v1))
        elif mode == "catmullrom":
            p0 = pts[i - 1] if i > 0 else (pts[0][0] - (pts[1][0] - pts[0][0]), pts[0][1])
            p3 = pts[i + 2] if i + 2 < len(pts) else (pts[-1][0] + (pts[-1][0] - pts[-2][0]), pts[-1][1])
            seg = [p0, pts[i], pts[i + 1], p3]
            for s in range(1, samples_per_seg):
                t = t0 + (t1 - t0) * s / samples_per_seg
                out.append((t, catmullrom(seg, t)))
            out.append((t1, v1))
        else:
            out.append((t1, v1))
    # clamp to animation length
    if length > 0:
        out = [(min(t, length), v) for t, v in out]
    return out


def parse_animations(anim_path):
    with open(anim_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    anims = data.get("animations", {})
    result = []
    for name, a in anims.items():
        length = float(a.get("animation_length", 0.0))
        bones = a.get("bones", {})
        channels = {}
        for bname, chans in bones.items():
            entry = {}
            for cname, raw in chans.items():
                if cname == "rotation":
                    entry["rotation"] = sample_channel(raw, length, "rotation")
                elif cname == "position":
                    entry["translation"] = sample_channel(raw, length, "translation")
                elif cname == "scale":
                    entry["scale"] = sample_channel(raw, length, "scale")
            if entry:
                channels[bname] = entry
        result.append({
            "name": name,
            "length": length,
            "loop": bool(a.get("loop", False)),
            "channels": channels,
        })
    return result


# --------------------------------------------------------------------------
# GLB writer
# --------------------------------------------------------------------------


class GLB:
    def __init__(self):
        self.json = {
            "asset": {"version": "2.0", "generator": "tacz_geo_to_glb"},
            "scene": 0,
            "scenes": [{"nodes": []}],
            "nodes": [],
            "meshes": [],
            "accessors": [],
            "bufferViews": [],
            "buffers": [{"byteLength": 0}],
            "materials": [],
            "textures": [],
            "images": [],
            "skins": [],
            "animations": [],
        }
        self.bin = bytearray()

    def align(self, n=4):
        while len(self.bin) % n:
            self.bin.append(0)

    def add_bytes(self, data, align=4):
        self.align(align)
        offset = len(self.bin)
        self.bin.extend(data)
        return offset, len(data)

    def add_buffer_view(self, data, target=None, align=4):
        offset, length = self.add_bytes(data, align)
        bv = {"buffer": 0, "byteOffset": offset, "byteLength": length}
        if target:
            bv["target"] = target
        self.json["bufferViews"].append(bv)
        return len(self.json["bufferViews"]) - 1

    def add_accessor(self, bv_idx, count, comp_type, acc_type, bounds=None):
        acc = {
            "bufferView": bv_idx,
            "componentType": comp_type,
            "count": count,
            "type": acc_type,
        }
        if bounds is not None:
            acc["min"], acc["max"] = bounds
        self.json["accessors"].append(acc)
        return len(self.json["accessors"]) - 1

    def finish(self, out_path):
        self.json["buffers"][0]["byteLength"] = len(self.bin)
        body = json.dumps(self.json, separators=(",", ":")).encode("utf-8")
        body += b" " * ((4 - len(body) % 4) % 4)
        bin_chunk = bytes(self.bin)
        bin_chunk += b"\x00" * ((4 - len(bin_chunk) % 4) % 4)
        total = 12 + 8 + len(body) + 8 + len(bin_chunk)
        with open(out_path, "wb") as f:
            f.write(struct.pack("<4sII", b"glTF", 2, total))
            f.write(struct.pack("<I4s", len(body), b"JSON"))
            f.write(body)
            f.write(struct.pack("<I4s", len(bin_chunk), b"BIN\x00"))
            f.write(bin_chunk)


def pack_vec(fmt, values):
    return struct.pack(fmt, *values)


def build_mesh_primitive(glb, positions, normals, uvs, joints, weights,
                         indices, material_idx, tex_w, tex_h):
    """Create a skinned mesh primitive; returns mesh index."""
    pos_bytes = struct.pack(f"<{len(positions)*3}f", *[c for v in positions for c in v])
    nor_bytes = struct.pack(f"<{len(normals)*3}f", *[c for v in normals for c in v])
    uv_bytes = struct.pack(f"<{len(uvs)*2}f", *[c for v in uvs for c in v])
    joint_bytes = struct.pack(f"<{len(joints)*4}B", *[j for v in joints for j in v])
    weight_bytes = struct.pack(f"<{len(weights)*4}f", *[w for v in weights for w in v])
    idx_bytes = struct.pack(f"<{len(indices)}I", *indices)

    bv_pos = glb.add_buffer_view(pos_bytes, 34962, 4)
    bv_nor = glb.add_buffer_view(nor_bytes, 34962, 4)
    bv_uv = glb.add_buffer_view(uv_bytes, 34962, 4)
    bv_jnt = glb.add_buffer_view(joint_bytes, 34962, 4)
    bv_wgt = glb.add_buffer_view(weight_bytes, 34962, 4)
    bv_idx = glb.add_buffer_view(idx_bytes, 34963, 4)

    min_p = [min(v[i] for v in positions) for i in range(3)]
    max_p = [max(v[i] for v in positions) for i in range(3)]
    acc_pos = glb.add_accessor(bv_pos, len(positions), 5126, "VEC3", (min_p, max_p))
    acc_nor = glb.add_accessor(bv_nor, len(normals), 5126, "VEC3")
    acc_uv = glb.add_accessor(bv_uv, len(uvs), 5126, "VEC2")
    acc_jnt = glb.add_accessor(bv_jnt, len(joints), 5121, "VEC4")
    acc_wgt = glb.add_accessor(bv_wgt, len(weights), 5126, "VEC4")
    acc_idx = glb.add_accessor(bv_idx, len(indices), 5125, "SCALAR")

    prim = {
        "attributes": {
            "POSITION": acc_pos,
            "NORMAL": acc_nor,
            "TEXCOORD_0": acc_uv,
            "JOINTS_0": acc_jnt,
            "WEIGHTS_0": acc_wgt,
        },
        "indices": acc_idx,
        "mode": 4,
    }
    if material_idx >= 0:
        prim["material"] = material_idx
    mesh_idx = len(glb.json["meshes"])
    glb.json["meshes"].append({"primitives": [prim]})
    return mesh_idx


def build_static_mesh(glb, positions, normals, uvs, indices, material_idx):
    """Create an unskinned static mesh primitive."""
    pos_bytes = struct.pack(f"<{len(positions)*3}f", *[c for v in positions for c in v])
    nor_bytes = struct.pack(f"<{len(normals)*3}f", *[c for v in normals for c in v])
    uv_bytes = struct.pack(f"<{len(uvs)*2}f", *[c for v in uvs for c in v])
    idx_bytes = struct.pack(f"<{len(indices)}I", *indices)
    bv_pos = glb.add_buffer_view(pos_bytes, 34962, 4)
    bv_nor = glb.add_buffer_view(nor_bytes, 34962, 4)
    bv_uv = glb.add_buffer_view(uv_bytes, 34962, 4)
    bv_idx = glb.add_buffer_view(idx_bytes, 34963, 4)
    min_p = [min(v[i] for v in positions) for i in range(3)]
    max_p = [max(v[i] for v in positions) for i in range(3)]
    acc_pos = glb.add_accessor(bv_pos, len(positions), 5126, "VEC3", (min_p, max_p))
    acc_nor = glb.add_accessor(bv_nor, len(normals), 5126, "VEC3")
    acc_uv = glb.add_accessor(bv_uv, len(uvs), 5126, "VEC2")
    acc_idx = glb.add_accessor(bv_idx, len(indices), 5125, "SCALAR")
    prim = {
        "attributes": {"POSITION": acc_pos, "NORMAL": acc_nor, "TEXCOORD_0": acc_uv},
        "indices": acc_idx,
        "mode": 4,
    }
    if material_idx >= 0:
        prim["material"] = material_idx
    mesh_idx = len(glb.json["meshes"])
    glb.json["meshes"].append({"primitives": [prim]})
    return mesh_idx


# --------------------------------------------------------------------------
# Main conversion
# --------------------------------------------------------------------------


def cube_geometry(cube, tex_w, tex_h, rot_order="XYZ"):
    """Emit positions/normals/uvs for one cube (absolute model space)."""
    origin = cube["origin"]
    size = cube["size"]
    inflate = cube["inflate"]
    cpivot = cube["pivot"]
    crot = cube["rotation"]
    uv = cube["uv"]

    frm = tuple(origin[i] - inflate for i in range(3))
    to = tuple(origin[i] + size[i] + inflate for i in range(3))

    # corner positions
    corners = {}
    for idx, (cx, cy, cz) in CORNERS.items():
        corners[idx] = (
            frm[0] + cx * (to[0] - frm[0]),
            frm[1] + cy * (to[1] - frm[1]),
            frm[2] + cz * (to[2] - frm[2]),
        )

    # per-face uv dict or legacy box uv
    if isinstance(uv, dict):
        face_uv = {k: v for k, v in uv.items()}
    else:
        u0, v0 = uv[0], uv[1]
        sx, sy, sz = size
        face_uv = {
            "east":  {"uv": [u0, v0], "uv_size": [sz, sy]},
            "west":  {"uv": [u0 + sz, v0], "uv_size": [sz, sy]},
            "north": {"uv": [u0 + 2 * sz, v0], "uv_size": [sx, sy]},
            "south": {"uv": [u0 + 2 * sz + sx, v0], "uv_size": [sx, sy]},
            "up":    {"uv": [u0 + sz, v0 + sy], "uv_size": [sx, sz]},
            "down":  {"uv": [u0 + sz + sx, v0 + sy], "uv_size": [sx, sz]},
        }

    positions, normals, uvs = [], [], []
    indices = []
    for fname, corners_list in FACES.items():
        if fname not in face_uv:
            continue
        fu = face_uv[fname]
        u0, v0 = fu.get("uv", [0.0, 0.0])
        us, vs = fu.get("uv_size", [size[0], size[1]])
        u2, v2 = u0 + us, v0 + vs
        quad = []
        for corner_idx, role in corners_list:
            du, dv = UV_ROLE[role]
            u = u0 if du == 0 else u2
            v = v0 if dv == 0 else v2
            quad.append((corner_idx, u, v))
        # outward normal from first 3 corners (already CCW)
        p0 = corners[quad[0][0]]
        p1 = corners[quad[1][0]]
        p2 = corners[quad[2][0]]
        e1 = v_sub(p1, p0)
        e2 = v_sub(p2, p0)
        n = (
            e1[1] * e2[2] - e1[2] * e2[1],
            e1[2] * e2[0] - e1[0] * e2[2],
            e1[0] * e2[1] - e1[1] * e2[0],
        )
        ln = v_len(n)
        if ln > 1e-9:
            n = v_scale(n, 1.0 / ln)
        else:
            n = (0.0, 1.0, 0.0)
        base = len(positions)
        for corner_idx, u, v in quad:
            positions.append(corners[corner_idx])
            normals.append(n)
            uvs.append((u / tex_w, 1.0 - v / tex_h))
        indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))
    return positions, normals, uvs, indices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", required=True)
    ap.add_argument("--anim", default=None)
    ap.add_argument("--texture", default=None)
    ap.add_argument("--normal", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split-bone", default=None)
    ap.add_argument("--out-mag", default=None)
    ap.add_argument("--pos-mode", default="replace", choices=["replace", "additive"])
    ap.add_argument("--rot-order", default="XYZ", choices=["XYZ", "ZYX"])
    ap.add_argument("--normalize-length", type=float, default=0.0,
                    help="scale so longest mesh axis == this length (e.g. 1.0 for meter scale); "
                         "0 disables. gun.gd clamps viewmodel scale to >=0.4 so pixel-unit models "
                         "would render huge without this.")
    ap.add_argument("--center", action="store_true",
                    help="translate mesh so AABB center == origin (matches gun.gd Mesh path which "
                         "re-centers via mi.position=-AABB_center; GLB path does not re-center, so "
                         "uncentered models get framed too high/close and look broken).")
    args = ap.parse_args()

    bones, roots, tex_w, tex_h = parse_geometry(args.geo)
    animations = parse_animations(args.anim) if args.anim else []

    glb = GLB()

    # --- material + images --------------------------------------------
    mat_idx = -1
    if args.texture:
        img_data = open(args.texture, "rb").read()
        img_bv = glb.add_buffer_view(img_data, None, 4)
        img_idx = len(glb.json["images"])
        glb.json["images"].append({"bufferView": img_bv, "mimeType": "image/png"})
        tex_idx = len(glb.json["textures"])
        glb.json["textures"].append({"source": img_idx})
        mat = {
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": tex_idx},
                "metallicFactor": 0.0,
                "roughnessFactor": 0.9,
            },
            "doubleSided": True,
        }
        glb.json["materials"].append(mat)
        mat_idx = 0

    # --- nodes ---------------------------------------------------------
    bone_index = {}
    for i, b in enumerate(bones):
        bone_index[b["name"]] = i

    root_node_idx = len(glb.json["nodes"])
    glb.json["nodes"].append({"name": "root"})

    node_idx = {}
    for i, b in enumerate(bones):
        node_idx[b["name"]] = len(glb.json["nodes"])
        glb.json["nodes"].append({"name": b["name"]})

    # build node TRS from rest rotation/pivot
    for b in bones:
        p = b["pivot"]
        r = b["rotation"]
        q = euler_quat(*r, args.rot_order)
        # translation = p - R*p  (identity at rest)
        rp = quat_rot_vec(q, p)
        t = tuple(p[i] - rp[i] for i in range(3))
        trs = {"translation": list(t), "rotation": list(q)}
        idx = node_idx[b["name"]]
        glb.json["nodes"][idx].update(trs)
        parent = b["parent"]
        if parent and parent in node_idx:
            glb.json["nodes"][node_idx[parent]].setdefault("children", []).append(idx)
        else:
            glb.json["nodes"][root_node_idx].setdefault("children", []).append(idx)
    glb.json["scenes"][0]["nodes"].append(root_node_idx)

    # --- mesh: all cubes except split subtree --------------------------
    split_name = args.split_bone
    split_root = bones[bone_index[split_name]] if split_name and split_name in bone_index else None
    split_names = set()
    if split_root:
        split_names.add(split_root["name"])
        for b in bones:
            node = b
            while node["parent"]:
                node = bones[bone_index[node["parent"]]]
                if node is split_root:
                    split_names.add(b["name"])
                    break

    all_pos, all_nor, all_uv, all_jnt, all_wgt, all_idx = [], [], [], [], [], []
    base_vertex = 0

    for b in bones:
        if b["name"] in split_names:
            continue
        bone_i = bone_index[b["name"]]
        for cube in b["cubes"]:
            qpos, qnor, quv, qidx = cube_geometry(cube, tex_w, tex_h, args.rot_order)
            # apply cube rotation about its own pivot (baked)
            if any(cube["rotation"]):
                qpos = [v_rot_euler(v, cube["pivot"], cube["rotation"], args.rot_order) for v in qpos]
                qnor = [mat_mul_vec(v_rot_matrix(cube["rotation"], args.rot_order), n) for n in qnor]
            cube_start = base_vertex
            all_pos.extend(qpos)
            all_nor.extend(qnor)
            all_uv.extend(quv)
            for _ in qpos:
                all_jnt.append((bone_i, 0, 0, 0))
                all_wgt.append((1.0, 0.0, 0.0, 0.0))
            all_idx.extend(i + cube_start for i in qidx)
            base_vertex += len(qpos)

    # 归一化：gun.gd 的 VIEWMODEL_LENGTH/extent 有 clampf(...,0.4,1.0) 下限，
    # 像素单位模型（如 TACZ 全长 ~43）必须缩到米级，否则第一人称下枪会巨大/破碎
    normalize_s = 1.0
    if args.normalize_length > 0.0 and all_pos:
        xs = [v[0] for v in all_pos]
        ys = [v[1] for v in all_pos]
        zs = [v[2] for v in all_pos]
        extent = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        if extent > 1e-6:
            normalize_s = args.normalize_length / extent
            all_pos = [v_scale(v, normalize_s) for v in all_pos]
            all_nor = list(all_nor)  # normals unaffected by uniform scale
    body_center = (0.0, 0.0, 0.0)
    if args.center and all_pos:
        xs = [v[0] for v in all_pos]
        ys = [v[1] for v in all_pos]
        zs = [v[2] for v in all_pos]
        body_center = (
            (min(xs) + max(xs)) / 2.0,
            (min(ys) + max(ys)) / 2.0,
            (min(zs) + max(zs)) / 2.0,
        )
        all_pos = [v_sub(v, body_center) for v in all_pos]
    print(f"normalize scale: {normalize_s:.6f}")
    print(f"body AABB center (subtract from model anchors/mag_offset): "
          f"{body_center[0]:.6f}, {body_center[1]:.6f}, {body_center[2]:.6f}")

    if all_pos:
        mesh_idx = build_mesh_primitive(
            glb, all_pos, all_nor, all_uv, all_jnt, all_wgt, all_idx,
            mat_idx, tex_w, tex_h,
        )
        gun_node = len(glb.json["nodes"])
        glb.json["nodes"].append({"name": "gun", "mesh": mesh_idx})
        glb.json["nodes"][root_node_idx].setdefault("children", []).append(gun_node)

    # --- skin ------------------------------------------------------------
    skin_joints = [node_idx[b["name"]] for b in bones]
    inv_bind = [1.0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1] * len(bones)
    ib_bytes = struct.pack(f"<{len(inv_bind)}f", *inv_bind)
    ib_bv = glb.add_buffer_view(ib_bytes, None, 4)
    ib_acc = glb.add_accessor(ib_bv, len(bones), 5126, "MAT4")
    skin_idx = len(glb.json["skins"])
    glb.json["skins"].append({
        "joints": skin_joints,
        "skeleton": root_node_idx,
        "inverseBindMatrices": ib_acc,
    })
    if "gun" in [n.get("name") for n in glb.json["nodes"]]:
        glb.json["nodes"][gun_node]["skin"] = skin_idx

    # --- animations --------------------------------------------------------
    # For each bone, merge rotation/translation/scale sample times onto a
    # shared timeline so the pivot-corrected translation always uses the
    # rotation from the same instant (T(p)*R*S*T(-p) node form).
    for anim in animations:
        if not anim["channels"]:
            continue
        channels = []
        samplers = []
        for bname, chans in anim["channels"].items():
            if bname not in node_idx:
                continue
            target_node = node_idx[bname]
            bone = bones[bone_index[bname]]
            rest_p = bone["pivot"]
            rest_r = bone["rotation"]

            rot_kfs = chans.get("rotation", [])
            trn_kfs = chans.get("translation", [])
            scl_kfs = chans.get("scale", [])
            if not (rot_kfs or trn_kfs or scl_kfs):
                continue

            # union of sample times
            times = sorted({k[0] for k in rot_kfs + trn_kfs + scl_kfs})

            def eval_at(kfs, t):
                """Linear-interpolate sampled channel at time t."""
                if not kfs:
                    return None
                if t <= kfs[0][0]:
                    return kfs[0][1]
                if t >= kfs[-1][0]:
                    return kfs[-1][1]
                for i in range(len(kfs) - 1):
                    t0, v0 = kfs[i]
                    t1, v1 = kfs[i + 1]
                    if t0 <= t <= t1:
                        if t1 == t0:
                            return v0
                        f = (t - t0) / (t1 - t0)
                        return tuple(v0[j] + (v1[j] - v0[j]) * f for j in range(3))
                return kfs[-1][1]

            rot_vals = []
            trn_vals = []
            scl_vals = []
            for t in times:
                e_anim = eval_at(rot_kfs, t)
                p_anim = eval_at(trn_kfs, t)
                s_anim = eval_at(scl_kfs, t)

                r_final = tuple(rest_r[i] + (e_anim[i] if e_anim else 0.0)
                                for i in range(3))
                q = euler_quat(*r_final, args.rot_order)

                if p_anim is not None:
                    if args.pos_mode == "additive":
                        p_f = tuple(rest_p[i] + p_anim[i] for i in range(3))
                    else:
                        p_f = p_anim
                else:
                    p_f = rest_p

                s_f = s_anim if s_anim is not None else (1.0, 1.0, 1.0)

                # node TRS for T(p) R S T(-p):
                #   translation = p - R*(S*p), rotation = R, scale = S
                sp = tuple(s_f[i] * p_f[i] for i in range(3))
                rsp = quat_rot_vec(q, sp)
                t_final = tuple(p_f[i] - rsp[i] for i in range(3))

                rot_vals.append(q)
                trn_vals.append(t_final)
                scl_vals.append(s_f)

            in_data = struct.pack(f"<{len(times)}f", *times)
            in_bv = glb.add_buffer_view(in_data, None, 4)
            in_acc = glb.add_accessor(in_bv, len(times), 5126, "SCALAR")

            for path, vals in (("rotation", rot_vals),
                               ("translation", trn_vals),
                               ("scale", scl_vals)):
                if path == "rotation":
                    out_data = struct.pack(f"<{len(vals)*4}f",
                                           *[c for v in vals for c in v])
                    comp_type, acc_type = 5126, "VEC4"
                else:
                    out_data = struct.pack(f"<{len(vals)*3}f",
                                           *[c for v in vals for c in v])
                    comp_type, acc_type = 5126, "VEC3"
                out_bv = glb.add_buffer_view(out_data, None, 4)
                out_acc = glb.add_accessor(out_bv, len(vals), comp_type, acc_type)
                samplers.append({
                    "input": in_acc,
                    "output": out_acc,
                    "interpolation": "LINEAR",
                })
                channels.append({
                    "sampler": len(samplers) - 1,
                    "target": {"node": target_node, "path": path},
                })
        if channels:
            glb.json["animations"].append({
                "name": anim["name"],
                "channels": channels,
                "samplers": samplers,
            })

    glb.finish(args.out)

    # --- optional split bone static GLB -------------------------------------
    if split_root and args.out_mag:
        mag_glb = GLB()
        mag_mat = -1
        if args.texture:
            img_data = open(args.texture, "rb").read()
            img_bv = mag_glb.add_buffer_view(img_data, None, 4)
            img_idx = len(mag_glb.json["images"])
            mag_glb.json["images"].append({"bufferView": img_bv, "mimeType": "image/png"})
            tex_idx = len(mag_glb.json["textures"])
            mag_glb.json["textures"].append({"source": img_idx})
            mag_glb.json["materials"].append({
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": tex_idx},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.9,
                },
                "doubleSided": True,
            })
            mag_mat = 0
        root = len(mag_glb.json["nodes"])
        mag_glb.json["nodes"].append({"name": "root"})
        mag_glb.json["scenes"][0]["nodes"].append(root)
        mpos, mnor, muv, midx = [], [], [], []
        base = 0
        for b in bones:
            if b["name"] not in split_names:
                continue
            for cube in b["cubes"]:
                qpos, qnor, quv, qidx = cube_geometry(cube, tex_w, tex_h, args.rot_order)
                if any(cube["rotation"]):
                    qpos = [v_rot_euler(v, cube["pivot"], cube["rotation"], args.rot_order) for v in qpos]
                    qnor = [mat_mul_vec(v_rot_matrix(cube["rotation"], args.rot_order), n) for n in qnor]
                cube_start = base
                mpos.extend(qpos)
                mnor.extend(qnor)
                muv.extend(quv)
                midx.extend(i + cube_start for i in qidx)
                base += len(qpos)
        if mpos:
            # 弹匣网格按 AABB 中心居中到自身原点（gun.gd 用 mag_offset 定位，语义与 Mesh 弹匣一致）
            mins = [min(v[i] for v in mpos) for i in range(3)]
            maxs = [max(v[i] for v in mpos) for i in range(3)]
            center = tuple((mins[i] + maxs[i]) / 2.0 for i in range(3))
            if args.normalize_length > 0.0:
                center = tuple(c * normalize_s for c in center)
                mpos = [v_scale(v, normalize_s) for v in mpos]
            if args.center:
                center = tuple(center[i] - body_center[i] for i in range(3))
            mpos = [v_sub(v, center) for v in mpos]
            mesh_idx = build_static_mesh(mag_glb, mpos, mnor, muv, midx, mag_mat)
            mag_node = len(mag_glb.json["nodes"])
            mag_glb.json["nodes"].append({"name": "mag", "mesh": mesh_idx})
            mag_glb.json["nodes"][root].setdefault("children", []).append(mag_node)
            print(f"mag center (use as mag_offset): {center[0]:.4f}, {center[1]:.4f}, {center[2]:.4f}")
        mag_glb.finish(args.out_mag)
        print(f"mag GLB written: {args.out_mag} ({base} verts)")

    print(f"GLB written: {args.out} ({len(all_pos)} verts, {len(animations)} animations)")


if __name__ == "__main__":
    main()
