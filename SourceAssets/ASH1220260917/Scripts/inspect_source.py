"""Dump the structure of the oden source FBX: objects, parts, materials, bounds.

Run:  blender --background --factory-startup --python-exit-code 1 --python inspect_source.py
"""
import json
import os
import sys

import bpy

SOURCE = r"D:\FPS3D\资产\oden先辈\fbx\weapon.FBX"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Reference")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SOURCE, use_custom_normals=True)

report = {"source": SOURCE, "objects": []}


def vec(v):
    return [round(float(c), 6) for c in v]


for obj in bpy.context.scene.objects:
    entry = {
        "name": obj.name,
        "type": obj.type,
        "location": vec(obj.location),
        "rotation_euler": vec(obj.rotation_euler),
        "scale": vec(obj.scale),
        "matrix_world_translation": vec(obj.matrix_world.translation),
    }
    if obj.type == "MESH":
        me = obj.data
        entry["vertices"] = len(me.vertices)
        entry["polygons"] = len(me.polygons)
        entry["dimensions"] = vec(obj.dimensions)
        entry["local_bbox_min"] = vec([min(v.co[i] for v in me.vertices) for i in range(3)])
        entry["local_bbox_max"] = vec([max(v.co[i] for v in me.vertices) for i in range(3)])
        entry["world_bbox_min"] = vec([min((obj.matrix_world @ v.co)[i] for v in me.vertices) for i in range(3)])
        entry["world_bbox_max"] = vec([max((obj.matrix_world @ v.co)[i] for v in me.vertices) for i in range(3)])
        entry["materials"] = [m.name if m else None for m in me.materials]
        entry["uv_layers"] = [uv.name for uv in me.uv_layers]
        entry["modifiers"] = [m.type for m in obj.modifiers]
        entry["vertex_groups"] = len(obj.vertex_groups)
        entry["parent"] = obj.parent.name if obj.parent else None
    report["objects"].append(entry)

# Material -> image map.
images = []
for mat in bpy.data.materials:
    info = {"name": mat.name, "use_nodes": mat.use_nodes, "textures": []}
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                info["textures"].append(
                    {"image": node.image.name, "filepath": node.image.filepath, "size": list(node.image.size)}
                )
    images.append(info)
report["materials"] = images

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if meshes:
    lo = [min(o["world_bbox_min"][i] for o in report["objects"] if o["type"] == "MESH") for i in range(3)]
    hi = [max(o["world_bbox_max"][i] for o in report["objects"] if o["type"] == "MESH") for i in range(3)]
    report["combined_world_bbox_min"] = vec(lo)
    report["combined_world_bbox_max"] = vec(hi)
    report["combined_world_size"] = vec([hi[i] - lo[i] for i in range(3)])

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "source_structure.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)

print("ASH12_INSPECT_BEGIN")
print(json.dumps(report, ensure_ascii=False, indent=1))
print("ASH12_INSPECT_END")
