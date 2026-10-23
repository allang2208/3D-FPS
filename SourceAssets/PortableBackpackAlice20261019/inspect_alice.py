import bpy
import json
import os

SRC = r"D:\FPS3D\VaultCache\FabLibrary\ALICE_Military_Backpack_-_Argentinean_Army-a4aeb32a\obj\mochila_low_poly.obj"
OUT_DIR = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=SRC)

objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
report = {"source": SRC, "objects": []}
for obj in objects:
    me = obj.data
    me.calc_loop_triangles()
    bbox_min = [min(v.co[i] for v in me.vertices) for i in range(3)]
    bbox_max = [max(v.co[i] for v in me.vertices) for i in range(3)]
    uv_layers = [layer.name for layer in me.uv_layers]
    groups = {}
    for vg in obj.vertex_groups:
        groups[vg.name] = 0
    for v in me.vertices:
        for g in v.groups:
            name = obj.vertex_groups[g.group].name
            groups[name] += 1
    mats = []
    for slot in obj.material_slots:
        mats.append({
            "slot": slot.name,
            "material": slot.material.name if slot.material else None,
        })
    report["objects"].append({
        "name": obj.name,
        "verts": len(me.vertices),
        "edges": len(me.edges),
        "polys": len(me.polygons),
        "tris": len(me.loop_triangles),
        "dimensions": list(obj.dimensions),
        "scale": list(obj.scale),
        "location": list(obj.location),
        "rotation_euler_deg": [round(a * 57.295779513, 4) for a in obj.rotation_euler],
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
        "uv_layers": uv_layers,
        "vertex_groups": groups,
        "material_slots": mats,
        "has_custom_normals": bool(me.has_custom_normals),
    })

report["scene_unit_scale"] = bpy.context.scene.unit_settings.scale_length
with open(os.path.join(OUT_DIR, "alice_inspect.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("ALICE_INSPECT " + json.dumps(report, ensure_ascii=False, default=str))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "AliceBackpack_raw.blend"))