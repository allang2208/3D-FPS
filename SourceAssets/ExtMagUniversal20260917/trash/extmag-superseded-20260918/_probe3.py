import bpy
from mathutils import Vector
FILES = [
 r"D:\FPS3D\FPSGAME\SourceAssets\SkeletonStock20260912\AKM_StockSections_Editable.blend",
 r"D:\FPS3D\FPSGAME\SourceAssets\PhantomRearGripIntegration20260913\AKM\AKM_RearGripSections_Editable.blend",
]
for path in FILES:
    print("PROBE3 FILE", path)
    try:
        bpy.ops.wm.open_mainfile(filepath=path)
    except Exception as e:
        print("PROBE3 open failed", e); continue
    for ob in bpy.data.objects:
        if ob.type != "MESH" or "AKM" not in ob.name:
            continue
        counts = {}
        for p in ob.data.polygons:
            counts[p.material_index] = counts.get(p.material_index, 0) + 1
        print("PROBE3 mesh", ob.name, "verts", len(ob.data.vertices), "polys", len(ob.data.polygons))
        print("PROBE3 slots", [(i, (m.name if m else None)) for i, m in enumerate(ob.data.materials)])
        print("PROBE3 faces_per_slot", counts)
        for idx, count in sorted(counts.items()):
            name = ob.data.materials[idx].name if idx < len(ob.data.materials) and ob.data.materials[idx] else "?"
            if "magazine" in name.lower():
                pts = [ob.matrix_world @ ob.data.vertices[v].co for p in ob.data.polygons if p.material_index == idx for v in p.vertices]
                lo = [round(min(p[i] for p in pts), 4) for i in range(3)]
                hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
                print("PROBE3 mag", name, "faces", count, "lo", lo, "hi", hi,
                      "dims_cm", [round((hi[i]-lo[i])*100, 2) for i in range(3)])
print("PROBE3_DONE")
