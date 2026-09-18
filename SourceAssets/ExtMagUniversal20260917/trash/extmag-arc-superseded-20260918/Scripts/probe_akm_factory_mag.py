"""Probe the AKM rifle FBX for its factory magazine geometry (read-only).

The runtime hides the factory magazine by material section name, so the same
section is what a rebuilt, lengthened AKM magazine should be derived from.
"""
import bpy
import os

RIFLE = r"D:\FPS3D\FPSGAME\SourceAssets\AKMSoviet20260911\SK_AKM_MannyNative.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=RIFLE)
print("PROBE objects", [(o.name, o.type) for o in bpy.context.scene.objects], flush=True)
for ob in list(bpy.context.scene.objects):
    if ob.type != "MESH":
        continue
    print("PROBE mesh", ob.name, "verts", len(ob.data.vertices), "polys", len(ob.data.polygons),
          "uv", [layer.name for layer in ob.data.uv_layers], flush=True)
    print("PROBE materials", [(i, m.name if m else None) for i, m in enumerate(ob.data.materials)], flush=True)
    counts = {}
    for poly in ob.data.polygons:
        counts[poly.material_index] = counts.get(poly.material_index, 0) + 1
    print("PROBE faces_per_slot", counts, flush=True)
    for index, count in sorted(counts.items()):
        name = ob.data.materials[index].name if index < len(ob.data.materials) and ob.data.materials[index] else "?"
        if "magazine" in name.lower():
            verts = set()
            for poly in ob.data.polygons:
                if poly.material_index == index:
                    verts.update(poly.vertices)
            co = [ob.data.vertices[v].co for v in verts]
            lo = [min(c[i] for c in co) for i in range(3)]
            hi = [max(c[i] for c in co) for i in range(3)]
            print("PROBE mag_section", name, "faces", count, "verts", len(verts),
                  "lo", [round(v, 4) for v in lo], "hi", [round(v, 4) for v in hi], flush=True)
print("PROBE_DONE", flush=True)
