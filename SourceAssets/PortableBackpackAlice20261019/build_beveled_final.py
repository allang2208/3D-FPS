import bpy
import bmesh
import math
import os
from mathutils import kdtree

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv.blend"))
low = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "SM_AliceBackpack")
mi = 3

# Isolate the hardware.
metal = low.copy()
metal.data = low.data.copy()
bpy.context.collection.objects.link(metal)
bm = bmesh.new(); bm.from_mesh(metal.data)
bad = [f for f in bm.faces if f.material_index != mi]
bmesh.ops.delete(bm, geom=bad, context="FACES")
bm.to_mesh(metal.data); bm.free(); metal.data.update()
for o in bpy.context.selected_objects: o.select_set(False)
metal.select_set(True); bpy.context.view_layer.objects.active = metal

# Bevel only substantial hardware edges; a global bevel collapses the many
# sub-millimetre edges and previously generated 1,253 zero-area faces.
attr = metal.data.attributes.get("bevel_w") or metal.data.attributes.new("bevel_w", "FLOAT", "EDGE")
bm = bmesh.new(); bm.from_mesh(metal.data); bm.edges.ensure_lookup_table()
edge_n = 0
for e in bm.edges:
    if len(e.link_faces) != 2 or e.calc_length() < 0.002:
        continue
    if min(f.calc_area() for f in e.link_faces) < 1e-7:
        continue
    try: ang = e.calc_face_angle(0.0)
    except ValueError: continue
    if ang >= math.radians(30.0):
        attr.data[e.index].value = 1.0
        edge_n += 1
bm.free()
bev = metal.modifiers.new("HardwareBevel", "BEVEL")
bev.width = 0.0006
bev.segments = 3
bev.limit_method = "WEIGHT"
bev.edge_weight = "bevel_w"
bev.use_clamp_overlap = True
bpy.ops.object.modifier_apply(modifier=bev.name)

# Remove only truly degenerate faces.
bm = bmesh.new(); bm.from_mesh(metal.data)
tiny = [f for f in bm.faces if f.calc_area() < 1e-12]
if tiny:
    bmesh.ops.delete(bm, geom=tiny, context="FACES")
bm.to_mesh(metal.data); bm.free()
for p in metal.data.polygons:
    p.use_smooth = True
metal.data.update()

# Bevel UV interpolation collapses a small number of faces.  Repair them by
# copying the nearest good loop UV; hardware is largely uniform steel.
layer = metal.data.uv_layers.active

def poly_uv_area(poly):
    pts = [layer.data[li].uv for li in poly.loop_indices]
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) * 0.5

bad0 = [p for p in metal.data.polygons if poly_uv_area(p) < 1e-10]
good = [p for p in metal.data.polygons if poly_uv_area(p) >= 1e-10]
coords, uvs = [], []
for p in good:
    for li in p.loop_indices:
        loop = metal.data.loops[li]
        coords.append(metal.data.vertices[loop.vertex_index].co)
        uvs.append(tuple(layer.data[li].uv))
kd = kdtree.KDTree(len(coords))
for i, co in enumerate(coords):
    kd.insert(co, i)
kd.balance()
for p in bad0:
    for li in p.loop_indices:
        co = metal.data.vertices[metal.data.loops[li].vertex_index].co
        _, idx, _ = kd.find(co)
        layer.data[li].uv = uvs[idx]
bad1 = [p for p in metal.data.polygons if poly_uv_area(p) < 1e-10]
print("ALICE_BEVEL edges", edge_n, "metal_faces", len(metal.data.polygons), "bad_uv_before", len(bad0), "bad_uv_after", len(bad1))

# Remove the old metal faces from the main mesh, then join the beveled hardware.
for o in bpy.context.selected_objects:
    o.select_set(False)
low.select_set(True)
bpy.context.view_layer.objects.active = low
bm = bmesh.new(); bm.from_mesh(low.data)
old_metal = [f for f in bm.faces if f.material_index == mi]
bmesh.ops.delete(bm, geom=old_metal, context="FACES")
bm.to_mesh(low.data); bm.free()
low.data.update()

bpy.ops.object.select_all(action="DESELECT")
low.select_set(True)
metal.select_set(True)
bpy.context.view_layer.objects.active = low
bpy.ops.object.join()
final = bpy.context.object
final.name = "SM_AliceBackpack"
final.data.name = "SM_AliceBackpack"
final.data.update()
print("ALICE_BEVEL final_verts", len(final.data.vertices), "faces", len(final.data.polygons), "materials", [m.name for m in final.data.materials])
print("ALICE_BEVEL uv_layers", [l.name for l in final.data.uv_layers])
print("ALICE_BEVEL dimensions", tuple(round(v, 5) for v in final.dimensions))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv_bevel.blend"))
print("ALICE_BEVEL saved")