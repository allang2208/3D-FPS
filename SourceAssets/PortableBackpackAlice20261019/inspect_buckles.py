import bpy
import bmesh
import math
import json
import os
from mathutils import Vector

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv_bevel.blend"))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "SM_AliceBackpack")

bm = bmesh.new(); bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
metal = [f for f in bm.faces if f.material_index == 3]
# connected components among metal faces
remaining = set(metal)
comps = []
while remaining:
    seed = remaining.pop()
    stack = [seed]; comp = [seed]
    while stack:
        f = stack.pop()
        for e in f.edges:
            for nf in e.link_faces:
                if nf in remaining and nf.material_index == 3:
                    remaining.remove(nf); stack.append(nf); comp.append(nf)
    comps.append(comp)
rows = []
for comp in comps:
    vs = {v for f in comp for v in f.verts}
    lo = [min(v.co[i] for v in vs) for i in range(3)]
    hi = [max(v.co[i] for v in vs) for i in range(3)]
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    d = [hi[i] - lo[i] for i in range(3)]
    # dominant normal
    n = Vector((0, 0, 0))
    for f in comp: n += f.normal * f.calc_area()
    n.normalize()
    rows.append({"faces": len(comp), "center": c, "dims": d, "normal": list(n), "lo": lo, "hi": hi})
bm.free()
rows.sort(key=lambda r: (-r["faces"], -r["dims"][0]*r["dims"][1]*r["dims"][2]))
print("METAL_COMPONENTS", len(rows))
for i, r in enumerate(rows[:25]):
    print("COMP", i, "faces", r["faces"], "c", [round(x, 4) for x in r["center"]], "d", [round(x, 4) for x in r["dims"]], "n", [round(x, 2) for x in r["normal"]])
with open(os.path.join(ROOT, "metal_components.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

# Histogram of components by x side and z
left = [r for r in rows if r["center"][0] < -0.05]
right = [r for r in rows if r["center"][0] > 0.05]
mid = [r for r in rows if -0.05 <= r["center"][0] <= 0.05]
print("SIDES", len(left), len(mid), len(right))
for label, group in (("LEFT", left), ("RIGHT", right)):
    print(label, "faces", sum(r["faces"] for r in group))
    for r in sorted(group, key=lambda r: -r["faces"])[:12]:
        print(" ", "f", r["faces"], "c", [round(x, 3) for x in r["center"]], "d", [round(x, 3) for x in r["dims"]], "n", [round(x, 2) for x in r["normal"]])