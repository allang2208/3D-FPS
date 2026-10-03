"""Extract the M-07 Meshy GLB into authoring data without editing the GLB.

This is a production data preparation step. It does not launch an engine,
render, test a runtime asset, or decide which source geometry should be cut.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image


COMPONENT_TYPES = {
    5120: np.dtype("i1"), 5121: np.dtype("u1"),
    5122: np.dtype("<i2"), 5123: np.dtype("<u2"),
    5125: np.dtype("<u4"), 5126: np.dtype("<f4"),
}
ARITY = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
         "MAT2": 4, "MAT3": 9, "MAT4": 16}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_glb(path: Path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67 or version != 2 or length != len(raw):
        raise ValueError("The supplied file is not a complete glTF 2 GLB")
    offset = 12
    document = None
    binary = None
    chunks = []
    while offset < len(raw):
        size, kind = struct.unpack_from("<II", raw, offset)
        content = raw[offset + 8:offset + 8 + size]
        chunks.append({"type": hex(kind), "bytes": size})
        if kind == 0x4E4F534A:
            document = json.loads(content.rstrip(b" \0").decode("utf-8"))
        elif kind == 0x004E4942:
            binary = content
        offset += 8 + size
    if document is None or binary is None:
        raise ValueError("JSON and embedded BIN chunks are required")
    return raw, document, binary, chunks


def accessor_array(document, binary, accessor_index):
    accessor = document["accessors"][accessor_index]
    if "sparse" in accessor:
        raise ValueError("Sparse accessors need an explicit extraction implementation")
    view = document["bufferViews"][accessor["bufferView"]]
    dtype = COMPONENT_TYPES[accessor["componentType"]]
    arity = ARITY[accessor["type"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", dtype.itemsize * arity)
    result = np.ndarray((accessor["count"], arity), dtype=dtype,
                        buffer=binary, offset=start, strides=(stride, dtype.itemsize)).copy()
    if accessor.get("normalized"):
        info = np.iinfo(dtype)
        result = result.astype(np.float32) / info.max
        if info.min < 0:
            result = np.maximum(result, -1.0)
    return result[:, 0] if arity == 1 else result


def texture_image_index(document, texture_info):
    texture = document["textures"][texture_info["index"]]
    return texture.get("source")


def extract_images(document, binary, target_dir):
    target_dir.mkdir(parents=True, exist_ok=True)
    semantics = {}
    for material_index, material in enumerate(document.get("materials", [])):
        pbr = material.get("pbrMetallicRoughness", {})
        references = {
            "basecolor": pbr.get("baseColorTexture"),
            "metallic_roughness": pbr.get("metallicRoughnessTexture"),
            "normal": material.get("normalTexture"),
            "occlusion": material.get("occlusionTexture"),
            "emissive": material.get("emissiveTexture"),
        }
        for semantic, info in references.items():
            if info:
                image_index = texture_image_index(document, info)
                semantics.setdefault(image_index, []).append({
                    "material_index": material_index, "semantic": semantic,
                    "texture_info": info,
                })
    records = []
    images = {}
    for image_index, image_doc in enumerate(document.get("images", [])):
        if "bufferView" not in image_doc:
            raise ValueError("Only embedded source images are supported here")
        view = document["bufferViews"][image_doc["bufferView"]]
        start = view.get("byteOffset", 0)
        payload = binary[start:start + view["byteLength"]]
        mime = image_doc.get("mimeType", "application/octet-stream")
        suffix = {"image/jpeg": ".jpg", "image/png": ".png"}.get(mime, ".bin")
        uses = semantics.get(image_index, [])
        primary_name = uses[0]["semantic"] if uses else f"image_{image_index:02d}"
        name = f"M07_{primary_name}_source{suffix}"
        out = target_dir / name
        out.write_bytes(payload)
        pil_image = Image.open(io.BytesIO(payload))
        images[image_index] = np.asarray(pil_image.convert("RGB"))
        record = {
            "image_index": image_index, "source_name": image_doc.get("name"),
            "mime_type": mime, "buffer_view": image_doc["bufferView"],
            "embedded_bytes": len(payload), "sha256": sha256(payload),
            "path": str(out), "dimensions": list(pil_image.size),
            "source_mode": pil_image.mode, "material_uses": uses,
            "derived_channels": [],
        }
        rgb = images[image_index]
        if any(use["semantic"] == "metallic_roughness" for use in uses):
            for channel_index, semantic in [(1, "roughness"), (2, "metallic")]:
                channel_path = target_dir / f"M07_{semantic}.png"
                Image.fromarray(rgb[:, :, channel_index], mode="L").save(channel_path)
                record["derived_channels"].append({
                    "semantic": semantic, "channel": "RGB"[channel_index],
                    "path": str(channel_path), "color_space": "linear data",
                })
        if any(use["semantic"] == "occlusion" for use in uses):
            channel_path = target_dir / "M07_occlusion.png"
            Image.fromarray(rgb[:, :, 0], mode="L").save(channel_path)
            record["derived_channels"].append({
                "semantic": "occlusion", "channel": "R", "path": str(channel_path),
                "color_space": "linear data",
            })
        records.append(record)
    return records, images


def vertex_color_samples(document, primitive, images, uv):
    material_index = primitive.get("material")
    if material_index is None:
        return None
    material = document["materials"][material_index]
    info = material.get("pbrMetallicRoughness", {}).get("baseColorTexture")
    if not info:
        return None
    texture = images[texture_image_index(document, info)]
    height, width = texture.shape[:2]
    # glTF image UV V=0 addresses the first image row. Blender import handles
    # the image orientation itself; samples here use glTF's original UVs.
    x = np.minimum((np.mod(uv[:, 0], 1.0) * width).astype(np.int64), width - 1)
    y = np.minimum((np.mod(uv[:, 1], 1.0) * height).astype(np.int64), height - 1)
    return texture[y, x].astype(np.float32) / 255.0


def color_summary(samples):
    if samples is None or len(samples) == 0:
        return None
    luminance = samples @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    return {"mean_rgb_srgb": samples.mean(axis=0).tolist(),
            "rgb_10_50_90_percentiles": np.percentile(samples, [10, 50, 90], axis=0).tolist(),
            "luminance_10_50_90_percentiles_srgb": np.percentile(luminance, [10, 50, 90]).tolist(),
            "blue_minus_red_mean_srgb": float((samples[:, 2] - samples[:, 0]).mean())}


def distribution(positions, triangles, colors):
    minimum, maximum = positions.min(axis=0), positions.max(axis=0)
    ys = (positions[:, 1] - minimum[1]) / (maximum[1] - minimum[1])
    centroids = positions[triangles].mean(axis=1)
    face_ys = (centroids[:, 1] - minimum[1]) / (maximum[1] - minimum[1])
    qs = [0, 1, 5, 25, 50, 75, 95, 99, 100]
    bands = []
    regions = [("central_body_candidate", 0.0, 0.16),
               ("intermediate_body_and_membrane", 0.16, 0.30),
               ("outer_membrane_candidate", 0.30, float("inf"))]
    for band in range(10):
        low, high = band / 10, (band + 1) / 10
        mask = (ys >= low) & ((ys < high) if band < 9 else (ys <= high))
        face_mask = (face_ys >= low) & ((face_ys < high) if band < 9 else (face_ys <= high))
        pts = positions[mask]
        entry = {"height_fraction_bottom_to_top": [low, high],
                 "y_range_source": [float(minimum[1] + low * (maximum[1] - minimum[1])),
                                    float(minimum[1] + high * (maximum[1] - minimum[1]))],
                 "vertex_count": int(mask.sum()), "triangle_centroid_count": int(face_mask.sum()),
                 "percentiles": qs,
                 "x_percentiles": np.percentile(pts[:, 0], qs).tolist() if len(pts) else [],
                 "z_percentiles": np.percentile(pts[:, 2], qs).tolist() if len(pts) else [],
                 "regions": []}
        for name, region_low, region_high in regions:
            rmask = mask & (np.abs(positions[:, 0]) >= region_low) & (np.abs(positions[:, 0]) < region_high)
            rfmask = face_mask & (np.abs(centroids[:, 0]) >= region_low) & (np.abs(centroids[:, 0]) < region_high)
            rpts = positions[rmask]
            entry["regions"].append({
                "name": name, "absolute_x_range_source": [region_low, region_high if np.isfinite(region_high) else None],
                "vertex_count": int(rmask.sum()), "triangle_centroid_count": int(rfmask.sum()),
                "z_5_50_95_percentiles": np.percentile(rpts[:, 2], [5, 50, 95]).tolist() if len(rpts) else [],
                "color": color_summary(colors[rmask]) if colors is not None else None,
            })
        bands.append(entry)
    return {"coordinate_convention": "glTF Y up; height measured from minimum Y; X lateral; Z depth",
            "region_threshold_note": "Coordinate masks are authoring hints, not semantic segmentation; no source faces are cut.",
            "height_bands": bands}


def welded_components(positions, triangles, tolerance=1e-6):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    quantized = np.rint(positions.astype(np.float64) / tolerance).astype(np.int64)
    _, first, inverse = np.unique(quantized, axis=0, return_index=True, return_inverse=True)
    wt = inverse[triangles]
    rows = np.concatenate((wt[:, 0], wt[:, 1], wt[:, 2]))
    cols = np.concatenate((wt[:, 1], wt[:, 2], wt[:, 0]))
    graph = coo_matrix((np.ones(len(rows), dtype=np.uint8), (rows, cols)),
                       shape=(len(first), len(first))).tocsr()
    count, labels = connected_components(graph, directed=False)
    vertex_sizes = np.bincount(labels, minlength=count)
    face_labels = labels[wt[:, 0]]
    triangle_sizes = np.bincount(face_labels, minlength=count)
    original_vertex_sizes = np.bincount(labels[inverse], minlength=count)
    order = np.argsort(vertex_sizes)[::-1]
    entries = []
    for label in order[:100]:
        pts = positions[first[labels == label]]
        entries.append({"component": int(label), "welded_vertices": int(vertex_sizes[label]),
                        "original_vertices": int(original_vertex_sizes[label]),
                        "triangles": int(triangle_sizes[label]),
                        "bounds_min": pts.min(axis=0).tolist(), "bounds_max": pts.max(axis=0).tolist()})
    return {"weld_tolerance_source_units": tolerance,
            "method": "rounded position cells; undirected triangle-edge connected components",
            "welded_vertex_count": len(first), "component_count": int(count),
            "largest_100_components": entries,
            "omitted_component_count": max(0, count - 100)}


def main():
    default_root = Path("D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001")
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=default_root)
    args = parser.parse_args()
    source = args.root / "Original/Meshy_AI_Veilwing_07_1001123357_texture.glb"
    authoring = args.root / "Authoring"
    authoring.mkdir(parents=True, exist_ok=True)
    raw, document, binary, chunks = read_glb(source)
    primitives = [(mi, pi, primitive) for mi, mesh in enumerate(document.get("meshes", []))
                  for pi, primitive in enumerate(mesh.get("primitives", []))]
    if len(primitives) != 1:
        raise ValueError("This authoring extraction expects exactly one source primitive")
    mesh_index, primitive_index, primitive = primitives[0]
    if primitive.get("mode", 4) != 4:
        raise ValueError("Triangle primitive required")
    attributes = primitive["attributes"]
    positions = accessor_array(document, binary, attributes["POSITION"]).astype(np.float32)
    normals = accessor_array(document, binary, attributes["NORMAL"]).astype(np.float32)
    uv = accessor_array(document, binary, attributes["TEXCOORD_0"]).astype(np.float32)
    indices = accessor_array(document, binary, primitive["indices"]).astype(np.uint32).reshape(-1, 3)
    npz_path = authoring / "source_mesh.npz"
    np.savez_compressed(npz_path, positions=positions, normals=normals, uvs=uv, indices=indices,
                        material_index=np.array(primitive.get("material", -1), dtype=np.int32))
    image_records, images = extract_images(document, binary, args.root / "Textures")
    colors = vertex_color_samples(document, primitive, images, uv)
    minimum, maximum = positions.min(axis=0), positions.max(axis=0)
    record = {
        "source": {"path": str(source), "bytes": len(raw), "sha256": sha256(raw),
                   "asset": document.get("asset"), "glb_chunks": chunks,
                   "source_is_unmodified": True},
        "coordinate_system": {"format": "glTF 2", "up_axis": "+Y", "handedness": "right",
                              "source_units": "glTF declares meters; generated scale is approximately 1.5046 m high",
                              "target_character_height_cm": 310,
                              "target_scale_factor_for_centimeters": float(310 / (maximum[1] - minimum[1])),
                              "geometry_space": "raw mesh accessor space; node transforms recorded below"},
        "mesh": {"mesh_index": mesh_index, "primitive_index": primitive_index,
                 "mesh_name": document["meshes"][mesh_index].get("name"),
                 "vertex_count": len(positions), "triangle_count": len(indices),
                 "attribute_accessors": attributes, "material_index": primitive.get("material"),
                 "bounds_min": minimum.tolist(), "bounds_max": maximum.tolist(),
                 "dimensions": (maximum - minimum).tolist(), "npz_path": str(npz_path),
                 "npz_keys": ["positions", "normals", "uvs", "indices", "material_index"]},
        "nodes": document.get("nodes", []), "scenes": document.get("scenes", []),
        "default_scene": document.get("scene"), "skins": document.get("skins", []),
        "animations": document.get("animations", []), "materials": document.get("materials", []),
        "textures": document.get("textures", []), "samplers": document.get("samplers", []),
        "texture_sources": image_records,
        "pbr_semantics": {"basecolor": "sRGB RGB and alpha if present",
                          "normal": "linear tangent-space glTF normal, positive green/Y; UE handling is downstream",
                          "metallic_roughness": "linear texture, roughness in G, metallic in B",
                          "occlusion": "linear R channel only when referenced by occlusionTexture",
                          "transparency": "Original glTF material alpha mode and factors are preserved in materials; no translucent material fabricated during extraction"},
        "authoring_distribution": distribution(positions, indices, colors),
        "connectivity": welded_components(positions, indices),
        "delivery_scope": "Source data and embedded PBR image extraction only; no model cuts, engine import, rendering, or runtime acceptance",
    }
    record_path = authoring / "source_structure.json"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"source_sha256": record["source"]["sha256"],
                      "vertex_count": len(positions), "triangle_count": len(indices),
                      "bounds_min": minimum.tolist(), "bounds_max": maximum.tolist(),
                      "dimensions": (maximum - minimum).tolist(),
                      "nodes": record["nodes"], "skin_count": len(record["skins"]),
                      "material_count": len(record["materials"]),
                      "textures": [{"path": r["path"], "dimensions": r["dimensions"], "uses": r["material_uses"]} for r in image_records],
                      "welded_vertices": record["connectivity"]["welded_vertex_count"],
                      "component_count": record["connectivity"]["component_count"],
                      "largest_components": record["connectivity"]["largest_100_components"][:12],
                      "npz_path": str(npz_path), "record_path": str(record_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
