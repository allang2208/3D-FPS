"""Reduce the approved textured GLB with meshoptimizer 0.2.30a0, keeping its original UV islands."""
from ctypes import c_float
import json
import struct
from pathlib import Path

import meshoptimizer
import numpy as np


PROJECT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT / "SourceAssets/VillageCarpenterNPC/Meshy/HeadR1/head.glb"
OUT = PROJECT / "SourceAssets/VillageCarpenterNPC/Head"


def main():
    with SOURCE.open("rb") as f:
        f.seek(12)
        json_size, chunk_type = struct.unpack("<I4s", f.read(8))
        if chunk_type != b"JSON":
            raise ValueError("Missing GLB JSON chunk")
        gltf = json.loads(f.read(json_size))
        f.read(8)
        binary_start = f.tell()

    def attribute(index):
        a = gltf["accessors"][index]
        v = gltf["bufferViews"][a["bufferView"]]
        dims = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        dtype = {5126: "<f4", 5125: "<u4", 5123: "<u2"}[a["componentType"]]
        offset = binary_start + v.get("byteOffset", 0) + a.get("byteOffset", 0)
        if "byteStride" in v:
            raise ValueError("This authoring input requires independent glTF attribute buffers")
        return np.memmap(SOURCE, dtype=dtype, mode="r", offset=offset, shape=(a["count"], dims))

    prim = gltf["meshes"][0]["primitives"][0]
    pos, normals, uv = (attribute(prim["attributes"][key]) for key in ("POSITION", "NORMAL", "TEXCOORD_0"))
    indices = attribute(prim["indices"]).ravel()
    result = np.empty(len(indices), dtype=np.uint32)
    attributes = np.column_stack((normals, uv))
    # The Meshy source has many small disconnected UV islands. Keep spatially distributed
    # representatives so the simplifier cannot spend the whole budget on atlas borders
    # while collapsing comparatively smooth landmarks such as the tip of the nose.
    grid = np.floor((pos - pos.min(axis=0)) / .018).astype(np.int32)
    cell = (grid[:, 0] * 256 + grid[:, 1]) * 256 + grid[:, 2]
    _, support = np.unique(cell, return_index=True)
    locks = np.zeros(len(pos), dtype=np.uint8)
    locks[support] = 1
    nose = int(np.argmax(pos[:, 2]))
    crown = int(np.argmax(pos[:, 1]))
    locks[[nose, crown]] = 1
    count = meshoptimizer.simplify_with_attributes(
        result, indices, pos, attributes, np.array([.065, .065, .065, .45, .45], np.float32),
        vertex_lock=locks, target_index_count=92_000 * 3, target_error=c_float(.024),
    )
    if not count:
        raise ValueError("The source surface could not be reduced")
    ids, new_indices = np.unique(result[:count], return_inverse=True)
    # glTF +Z is forward; the R4 body uses +Y forward and +Z up. Keep UE's clockwise winding.
    np.savez_compressed(OUT / "game_surface.npz", p=pos[ids][:, [0, 2, 1]], n=normals[ids][:, [0, 2, 1]],
                        uv=uv[ids], tri=new_indices.reshape(-1, 3).astype(np.int32),
                        crown=pos[crown, 1], nose=pos[nose, [0, 2, 1]])
    report = {"source_triangles": len(indices) // 3, "reduced_triangles": count // 3,
              "vertices": len(ids), "source": str(SOURCE), "method": "meshoptimizer UV and normal weighted collapse"}
    (OUT / "reduction.json").write_text(json.dumps(report, indent=2))
    print(report, flush=True)


if __name__ == "__main__":
    main()
