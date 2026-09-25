"""Inspect D:/FPS3D/source glb before bow-part import."""
from __future__ import annotations

import json
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
SRC = Path("D:/FPS3D") / "资产" / "source.glb"
OUT = HERE / "inspect_source.json"
(HERE / "InspectPreview").mkdir(exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0


def bbox(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs, ys, zs = zip(*[(p.x, p.y, p.z) for p in pts])
    return {
        "min_m": [min(xs), min(ys), min(zs)],
        "max_m": [max(xs), max(ys), max(zs)],
        "size_m": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
        "center_m": [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2],
        "size_cm": [(max(xs) - min(xs)) * 100, (max(ys) - min(ys)) * 100, (max(zs) - min(zs)) * 100],
    }


def mesh_info(obj):
    mesh = obj.data
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    mats = []
    for i, slot in enumerate(obj.material_slots):
        mat = slot.material
        item = {"index": i, "name": slot.name or (mat.name if mat else ""), "users": 0, "nodes": []}
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    item["nodes"].append(
                        {
                            "image": node.image.name,
                            "size": list(node.image.size),
                            "filepath": node.image.filepath,
                        }
                    )
        mats.append(item)
    counts = [0] * max(1, len(mesh.materials) or 1)
    for poly in mesh.polygons:
        if poly.material_index < len(counts):
            counts[poly.material_index] += 1
    for i, count in enumerate(counts):
        if i < len(mats):
            mats[i]["users"] = count
    return {
        "name": obj.name,
        "tris": tris,
        "verts": len(mesh.vertices),
        "polys": len(mesh.polygons),
        "materials": mats,
        "bbox": bbox(obj),
    }


def thin_islands(obj, max_span_m=0.004):
    hits = []
    mesh = obj.data
    world = obj.matrix_world
    for i, poly in enumerate(mesh.polygons):
        pts = [world @ mesh.vertices[v].co for v in poly.vertices]
        xs, ys, zs = zip(*[(p.x, p.y, p.z) for p in pts])
        size = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        thin = sum(1 for s in size if s <= max_span_m)
        long = max(size)
        if thin >= 2 and long > 0.2:
            hits.append({"face": i, "size_m": size, "mat": poly.material_index})
            if len(hits) >= 40:
                break
    return hits


reset()
if not SRC.is_file():
    raise SystemExit("missing " + str(SRC))
bpy.ops.import_scene.gltf(filepath=str(SRC))

objects = [o for o in bpy.data.objects if o.type == "MESH"]
report = {
    "source": str(SRC),
    "bytes": SRC.stat().st_size,
    "objects": [],
    "scene_bbox_m": None,
    "scene_size_cm": None,
}
all_pts = []
for obj in objects:
    info = mesh_info(obj)
    info["thin_long_faces"] = thin_islands(obj)
    report["objects"].append(info)
    all_pts.extend([obj.matrix_world @ v.co for v in obj.data.vertices])

if all_pts:
    xs, ys, zs = zip(*[(p.x, p.y, p.z) for p in all_pts])
    size = [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)]
    report["scene_bbox_m"] = {
        "min": [min(xs), min(ys), min(zs)],
        "max": [max(xs), max(ys), max(zs)],
        "size": size,
        "center": [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2],
    }
    report["scene_size_cm"] = [c * 100 for c in size]

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(
    "WOOD_LONGBOW_INSPECT",
    json.dumps(
        {
            "objects": len(report["objects"]),
            "size_cm": report["scene_size_cm"],
            "names": [o["name"] for o in report["objects"]],
            "tris": [o["tris"] for o in report["objects"]],
        }
    ),
    flush=True,
)