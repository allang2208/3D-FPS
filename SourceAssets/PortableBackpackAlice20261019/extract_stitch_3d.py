import bpy
import json
import os
from collections import defaultdict
from math import degrees

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_baked.blend"))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "SM_AliceBackpack")
me = obj.data
uv = me.uv_layers.active.data
MATS = ["Canvas", "Webbing", "Leather", "Metal"]
edge_faces = defaultdict(list)
for poly in me.polygons:
    loops = list(poly.loop_indices)
    for k, li in enumerate(loops):
        a = me.loops[li]
        b = me.loops[loops[(k + 1) % len(loops)]]
        key = (min(a.vertex_index, b.vertex_index), max(a.vertex_index, b.vertex_index))
        edge_faces[key].append(poly.index)

segments = defaultdict(list)
for key, faces in edge_faces.items():
    if len(faces) != 2:
        continue
    p0, p1 = me.polygons[faces[0]], me.polygons[faces[1]]
    if p0.material_index != p1.material_index:
        continue
    mat = MATS[p0.material_index]
    if mat == "Metal":
        continue
    if not (p0.normal.length and p1.normal.length):
        continue
    angle = degrees(p0.normal.angle(p1.normal))
    va, vb = me.vertices[key[0]].co, me.vertices[key[1]].co
    length = (va - vb).length
    if angle < 55.0 or length < 0.004:
        continue
    poly = p0
    loops = list(poly.loop_indices)
    uv_by_vertex = {}
    for li in loops:
        loop = me.loops[li]
        uv_by_vertex[loop.vertex_index] = tuple(uv[li].uv)
    if key[0] not in uv_by_vertex or key[1] not in uv_by_vertex:
        continue
    n = (p0.normal + p1.normal).normalized()
    segments[mat].append({
        "uv": [round(uv_by_vertex[key[0]][0], 6), round(uv_by_vertex[key[0]][1], 6),
               round(uv_by_vertex[key[1]][0], 6), round(uv_by_vertex[key[1]][1], 6)],
        "p1": [round(va.x, 7), round(va.y, 7), round(va.z, 7)],
        "p2": [round(vb.x, 7), round(vb.y, 7), round(vb.z, 7)],
        "n": [round(n.x, 6), round(n.y, 6), round(n.z, 6)],
        "length": round(length, 7),
    })

# Deduplicate by 3D endpoints and UV.
for mat in segments:
    seen = set()
    clean = []
    for s in segments[mat]:
        key = (tuple(s["uv"]), tuple(s["p1"]), tuple(s["p2"]))
        if key in seen:
            continue
        seen.add(key)
        clean.append(s)
    segments[mat] = clean
    total = sum(s["length"] for s in clean)
    print("ALICE_STITCH3D", mat, len(clean), "total_m", round(total, 3))

with open(os.path.join(ROOT, "stitch_segments_3d.json"), "w", encoding="utf-8") as f:
    json.dump(segments, f, ensure_ascii=False)
with open(os.path.join(ROOT, "stitch_segments.json"), "w", encoding="utf-8") as f:
    json.dump({mat: [s["uv"] for s in segs] for mat, segs in segments.items()}, f, ensure_ascii=False)
print("ALICE_STITCH3D done", {k: len(v) for k, v in segments.items()})