"""Read the authoritative geometry straight out of the glTF export.

The UE side has been edited many times by hand-written patch scripts, so the
saved .umap no longer tells us what the source actually contains. The glTF is
the Blender export that everything was imported from, and it carries the real
triangles. This dumps them in UE space (cm, Y flipped) so the level can be
rebuilt against measured numbers instead of guesses.

Blender (Z up) -> glTF (Y up):  gx = bx, gy = bz, gz = -by
glTF -> UE (Z up, cm):          ue = (gx*100, gz*100, gy*100)

The Y term is +gz (not -gz). Verified against the bounds UE itself reports for
the imported actors: e.g. S_balcony_glass is at glTF z = +2.79, and UE has the
railing at y = +279; S_glazing spans glTF z -9.56..+0.14 and UE reports
y -956..+14. A -gz mapping mirrors the whole apartment across y = 0, which is
how the door and spawn scripts ended up on the wrong side of the building.

Writes Saved/_gltf_geometry.json plus a short human-readable summary.
"""
import json
import os
import struct
import sys

import numpy as np

EXPORT = r"D:\CyberpunkApartment\export"
GLTF = os.path.join(EXPORT, "CyberpunkApartment.gltf")
OUT = r"D:\FPS3D\FPSGAME\Saved\_gltf_geometry.json"

COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
             5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load_buffers(gltf):
    blobs = []
    for buf in gltf.get("buffers", []):
        uri = buf.get("uri", "")
        if uri.startswith("data:"):
            raise RuntimeError("embedded buffer not supported")
        with open(os.path.join(EXPORT, uri), "rb") as fh:
            blobs.append(fh.read())
    return blobs


def read_accessor(gltf, blobs, index):
    acc = gltf["accessors"][index]
    fmt, size = COMPONENT[acc["componentType"]]
    n = NCOMP[acc["type"]]
    count = acc["count"]
    if "bufferView" not in acc:
        return np.zeros((count, n), dtype=np.float64)
    view = gltf["bufferViews"][acc["bufferView"]]
    blob = blobs[view.get("buffer", 0)]
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride") or size * n
    out = np.empty((count, n), dtype=np.float64)
    for i in range(count):
        off = start + i * stride
        out[i] = struct.unpack_from("<" + fmt * n, blob, off)
    return out


def node_matrix(node):
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
    t = node.get("translation", [0, 0, 0])
    r = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    x, y, z, w = r
    rot = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0],
        [0, 0, 0, 1]], dtype=np.float64)
    m = np.eye(4)
    m[:3, :3] = rot[:3, :3] * np.array(s)
    m[:3, 3] = t
    return m


def to_ue(p):
    """glTF (Y up) -> UE (Z up, cm)."""
    return np.column_stack([p[:, 0] * 100.0, p[:, 2] * 100.0, p[:, 1] * 100.0])


def main():
    with open(GLTF, "r", encoding="utf-8") as fh:
        gltf = json.load(fh)
    blobs = load_buffers(gltf)

    scene = gltf["scenes"][gltf.get("scene", 0)]
    report = {"meshes": {}, "notes": []}

    def walk(ni, parent):
        node = gltf["nodes"][ni]
        m = parent @ node_matrix(node)
        if "mesh" in node:
            mesh = gltf["meshes"][node["mesh"]]
            allpos, allidx = [], []
            base = 0
            for prim in mesh["primitives"]:
                pos = read_accessor(gltf, blobs, prim["attributes"]["POSITION"])
                pos = np.column_stack([pos, np.ones(len(pos))]) @ m.T
                pos = pos[:, :3]
                allpos.append(pos)
                if "indices" in prim:
                    idx = read_accessor(gltf, blobs, prim["indices"]).astype(np.int64)
                    allidx.append(idx.ravel() + base)
                else:
                    allidx.append(np.arange(base, base + len(pos)))
                base += len(pos)
            pos = to_ue(np.vstack(allpos))
            idx = np.concatenate(allidx) if allidx else np.zeros(0, dtype=np.int64)
            tri = idx.reshape(-1, 3) if len(idx) else np.zeros((0, 3), dtype=np.int64)
            # drop degenerate triangles (zero-thickness quads export fine; these are real)
            if len(tri):
                a, b, c = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
                area2 = np.linalg.norm(np.cross(b - a, c - a), axis=1)
                tri = tri[area2 > 1e-9]
            report["meshes"][node.get("name", "mesh%d" % node["mesh"])] = {
                "verts": int(len(pos)),
                "tris": int(len(tri)),
                "min": [round(float(v), 2) for v in pos.min(axis=0)],
                "max": [round(float(v), 2) for v in pos.max(axis=0)],
                "positions": np.round(pos, 2).tolist(),
                "indices": tri.ravel().tolist(),
            }
        for ch in node.get("children", []):
            walk(ch, m)

    for ni in scene["nodes"]:
        walk(ni, np.eye(4))

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh)

    print("%-24s %8s %8s  %s" % ("mesh", "verts", "tris", "UE bounds (cm)"))
    for name in sorted(report["meshes"]):
        m = report["meshes"][name]
        print("%-24s %8d %8d  x %8.1f..%8.1f  y %9.1f..%9.1f  z %8.1f..%8.1f" % (
            name, m["verts"], m["tris"], m["min"][0], m["max"][0],
            m["min"][1], m["max"][1], m["min"][2], m["max"][2]))
    print("\nwrote", OUT)


if __name__ == "__main__":
    sys.exit(main())
