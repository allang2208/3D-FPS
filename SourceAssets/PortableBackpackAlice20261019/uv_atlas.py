import bpy
import json
import math
import os

SRC = os.environ.get("ALICE_UV_SRC", r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019\AliceBackpack_prepared.blend")
OUT_DIR = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"

bpy.ops.wm.open_mainfile(filepath=SRC)
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
me = obj.data

while me.uv_layers:
    me.uv_layers.remove(me.uv_layers[0])
uv = me.uv_layers.new(name="UV_AliceAtlas")
me.uv_layers.active = uv

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

# Each material gets a full 0-1 packing.  The material groups overlap in UV0,
# but they render with separate textures, so this preserves texel density for
# the small leather/metal parts instead of letting the canvas eat the atlas.
for mi, slot in enumerate(obj.material_slots):
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in me.polygons:
        p.select = (p.material_index == mi)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(66.0),
        island_margin=0.006,
        area_weight=0.0,
        correct_aspect=True,
        scale_to_bounds=False,
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    print("ALICE_UV packed", slot.material.name)

# Report each material's UV coverage.
report = {"uv_layer": me.uv_layers.active.name, "materials": []}
uv_data = me.uv_layers.active.data
for mi, slot in enumerate(obj.material_slots):
    us, vs, area, zero = [], [], 0.0, 0
    for p in me.polygons:
        if p.material_index != mi:
            continue
        pts = [(uv_data[i].uv.x, uv_data[i].uv.y) for i in p.loop_indices]
        us.extend(x for x, y in pts)
        vs.extend(y for x, y in pts)
        a = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            a += x1 * y2 - x2 * y1
        a *= 0.5
        if abs(a) < 1e-10:
            zero += 1
        area += abs(a)
    report["materials"].append({
        "slot": mi,
        "material": slot.material.name,
        "faces": sum(1 for p in me.polygons if p.material_index == mi),
        "bbox": [min(us), min(vs), max(us), max(vs)],
        "face_area_sum": area,
        "zero_area_faces": zero,
    })

OUT_BLEND = os.environ.get("ALICE_UV_OUT", os.path.join(OUT_DIR, "AliceBackpack_uv.blend"))
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
RECEIPT = os.environ.get("ALICE_UV_RECEIPT", os.path.join(OUT_DIR, "uv_atlas_receipt.json"))
with open(RECEIPT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("ALICE_UV_ATLAS " + json.dumps(report, ensure_ascii=False, default=str))
