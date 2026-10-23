import bpy
import json
import math
import os

SRC = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019\AliceBackpack_raw.blend"
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019\alice_uv_probe.json"

bpy.ops.wm.open_mainfile(filepath=SRC)
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
me = obj.data
uv = me.uv_layers.active.data
report = {"object": obj.name, "materials": []}

for mi, slot in enumerate(obj.material_slots):
    polys = [p for p in me.polygons if p.material_index == mi]
    if not polys:
        continue
    us = []
    vs = []
    uv_area = 0.0
    bad = 0
    for p in polys:
        loops = list(p.loop_indices)
        pts = [(uv[i].uv.x, uv[i].uv.y) for i in loops]
        us.extend(x for x, y in pts)
        vs.extend(y for x, y in pts)
        a = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            a += x1 * y2 - x2 * y1
        a *= 0.5
        if abs(a) < 1e-10:
            bad += 1
        uv_area += abs(a)
    report["materials"].append({
        "slot": mi,
        "name": slot.material.name if slot.material else slot.name,
        "faces": len(polys),
        "uv_bbox": [min(us), min(vs), max(us), max(vs)],
        "uv_face_area_sum": uv_area,
        "zero_area_faces": bad,
        "outside_0_1": sum(1 for x in us if x < -1e-6 or x > 1 + 1e-6) + sum(1 for y in vs if y < -1e-6 or y > 1 + 1e-6),
    })

# world-space extents per material after applying object rotation
for mi, entry in enumerate(report["materials"]):
    polys = [p for p in me.polygons if p.material_index == mi]
    coords = []
    for p in polys:
        for vi in p.vertices:
            co = obj.matrix_world @ me.vertices[vi].co
            coords.append((co.x, co.y, co.z))
    if coords:
        entry["world_bbox"] = [
            [min(c[i] for c in coords) for i in range(3)],
            [max(c[i] for c in coords) for i in range(3)],
        ]

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("ALICE_UV " + json.dumps(report, ensure_ascii=False, default=str))