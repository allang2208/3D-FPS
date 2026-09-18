"""Probe the section blends for reusable factory-magazine geometry (read-only).

The icon audit already renders each rifle's factory magazine as a single piece,
so the same objects are the right input for a factory-grade extended magazine.
"""
import bpy
import os
import sys
from mathutils import Vector

SA = r"D:\FPS3D\FPSGAME\SourceAssets"
BLENDS = [
    (r"PhantomRearGripIntegration20260913\AKM\AKM_RearGripSections_Editable.blend", "AKM"),
    (r"PhantomRearGripIntegration20260913\QBZ191\QBZ191_RearGripSections_Editable.blend", "QBZ"),
    (r"PhantomRearGripIntegration20260913\M4\M4_RearGripSections_Editable.blend", "M4"),
]


def bounds(ob, matrix):
    pts = [matrix @ Vector(corner) for corner in ob.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


for rel, tag in BLENDS:
    path = os.path.join(SA, rel)
    print("PROBE_BLEND", tag, os.path.exists(path), flush=True)
    if not os.path.exists(path):
        continue
    bpy.ops.wm.open_mainfile(filepath=path)
    print("PROBE objects", [(o.name, o.type) for o in bpy.data.objects], flush=True)
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        lo, hi = bounds(ob, ob.matrix_world)
        print("PROBE mesh", tag, ob.name, "verts", len(ob.data.vertices),
              "polys", len(ob.data.polygons),
              "mats", [m.name if m else None for m in ob.data.materials],
              "uv", [layer.name for layer in ob.data.uv_layers],
              "mods", [m.type for m in ob.modifiers],
              "groups", len(ob.vertex_groups),
              "lo", tuple(round(v, 4) for v in lo), "hi", tuple(round(v, 4) for v in hi),
              "dims_cm", tuple(round((hi - lo)[i] * 100, 2) for i in range(3)),
              "parent", ob.parent.name if ob.parent else None, flush=True)
print("PROBE_DONE", flush=True)
