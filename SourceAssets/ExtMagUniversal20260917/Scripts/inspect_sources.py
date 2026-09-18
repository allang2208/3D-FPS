"""Inspect the three rifles' source FBX plus accepted drum meshes.

Reports, per file: mesh objects with world-space bounding boxes, material slot
names, and the WPN_SOCKET_Magazine / WPN_root bone transforms from the
armature. Output is one JSON per file in ../Reference.
Run:  blender -b -P inspect_sources.py -- <fbx> [<fbx> ...]
"""
import bpy
import json
import math
import os
import sys

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Reference")
OUT_DIR = os.path.normpath(OUT_DIR)

TRACKED_BONES = ("WPN_root", "WPN_SOCKET_Magazine")


def bbox_world(obj):
    corners = [obj.matrix_world @ __import__("mathutils").Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return {
        "min": [min(xs), min(ys), min(zs)],
        "max": [max(xs), max(ys), max(zs)],
        "size": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
    }


def inspect(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    report = {"file": path, "objects": [], "bones": {}}
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            mats = [ms.name if ms else "" for ms in obj.material_slots]
            report["objects"].append({
                "name": obj.name,
                "mats": mats,
                "bbox": bbox_world(obj),
                "verts": len(obj.data.vertices),
            })
        elif obj.type == "ARMATURE":
            for bone in obj.data.bones:
                if bone.name in TRACKED_BONES:
                    # Head/tail in armature space; convert to world for comparability.
                    head = obj.matrix_world @ bone.head_local
                    tail = obj.matrix_world @ bone.tail_local
                    axis = tail - head
                    length = axis.length
                    report["bones"][bone.name] = {
                        "head": [head.x, head.y, head.z],
                        "tail": [tail.x, tail.y, tail.z],
                        "axis_dir": [axis.x / length, axis.y / length, axis.z / length] if length else [0, 0, 1],
                        "parent": bone.parent.name if bone.parent else "",
                    }
    out = os.path.join(OUT_DIR, os.path.splitext(os.path.basename(path))[0] + "." + os.path.basename(os.path.dirname(path)) + ".inspect.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("WROTE", out)


for p in ARGS:
    inspect(p)
