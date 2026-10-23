import bpy
import bmesh
import math
import os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
BASE = os.path.join(ROOT, "AliceBackpack_uv_bevel_prebuckle.blend")
if not os.path.exists(BASE):
    BASE = os.path.join(ROOT, "AliceBackpack_uv_bevel.blend")
bpy.ops.wm.open_mainfile(filepath=BASE)
low = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "SM_AliceBackpack")

# Isolate all hardware, then split its eight loose parts so a cut can never
# remove geometry from a neighbouring buckle or from cloth.
metal = low.copy()
metal.data = low.data.copy()
bpy.context.collection.objects.link(metal)
metal.name = "SM_AliceBackpack_Hardware"
bm = bmesh.new(); bm.from_mesh(metal.data)
bad = [f for f in bm.faces if f.material_index != 3]
bmesh.ops.delete(bm, geom=bad, context="FACES")
bm.to_mesh(metal.data); bm.free(); metal.data.update()
for o in bpy.context.selected_objects: o.select_set(False)
metal.select_set(True); bpy.context.view_layer.objects.active = metal
bpy.ops.mesh.separate(type="LOOSE")
pieces = [o for o in bpy.context.selected_objects if o.type == "MESH"]
print("BUCKLE_PIECES", [(len(o.data.polygons)) for o in pieces])

def centroid(o):
    vs = [v.co for v in o.data.vertices]
    return [sum(v[i] for v in vs) / len(vs) for i in range(3)]

def poly_uv_area(layer, p):
    pts = [layer.data[li].uv for li in p.loop_indices]
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) * 0.5

def uv_bad(o):
    layer = o.data.uv_layers.active
    return sum(1 for p in o.data.polygons if poly_uv_area(layer, p) < 1e-10)

def cut_piece(piece, loc, dims, cutter_size, label):
    before = len(piece.data.polygons)
    for o in bpy.context.selected_objects: o.select_set(False)
    piece.select_set(True); bpy.context.view_layer.objects.active = piece
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    cut = bpy.context.object
    cut.name = "Cut_" + label
    cut.scale = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bev = cut.modifiers.new("CutterBevel", "BEVEL")
    bev.width = cutter_size
    bev.segments = 3
    bpy.ops.object.modifier_apply(modifier=bev.name)
    for o in bpy.context.selected_objects: o.select_set(False)
    piece.select_set(True); bpy.context.view_layer.objects.active = piece
    mod = piece.modifiers.new("Open_" + label, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cut
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cut, do_unlink=True)
    bv = BVHTree.FromObject(piece, bpy.context.evaluated_depsgraph_get())
    if label.startswith("Front"):
        origin = Vector((loc[0], -0.25, loc[2])); direction = Vector((0, 1, 0))
    else:
        origin = Vector((loc[0] - 0.10 if loc[0] < 0 else loc[0] + 0.10, loc[1], loc[2]))
        direction = Vector((1, 0, 0)) if loc[0] < 0 else Vector((-1, 0, 0))
    hit = bv.ray_cast(origin, direction, 0.3)
    print("BUCKLE_CUT", label, "faces", before, "->", len(piece.data.polygons), "bad_uv", uv_bad(piece), "through", hit[0] is None)

# Front left/right release buckles: one rounded window through the front plate.
for label, target_count, loc in (
    ("FrontLeft", 1567, (-0.0617, -0.1392, 0.1329)),
    ("FrontRight", 1567, (0.0617, -0.1392, 0.1329)),
):
    piece = min((o for o in pieces if len(o.data.polygons) == target_count),
                key=lambda o: sum((centroid(o)[i] - loc[i]) ** 2 for i in range(3)))
    cut_piece(piece, loc, (0.012, 0.030, 0.007), 0.0014, label)

# Side compression buckles: through-slot on the main 787-face body.  The small
# 177-face release button is left intact so it reads as a pressable tab in the
# opening instead of a solid plate.
for label, loc in (
    ("SideLeft", (-0.2361, -0.0800, -0.0346)),
    ("SideRight", (0.2408, -0.0723, -0.0433)),
):
    piece = min((o for o in pieces if len(o.data.polygons) == 787),
                key=lambda o: sum((centroid(o)[i] - loc[i]) ** 2 for i in range(3)))
    cut_piece(piece, loc, (0.030, 0.014, 0.014), 0.0012, label)

# Join all hardware pieces back into a single metal object.
for o in bpy.context.selected_objects: o.select_set(False)
for o in pieces: o.select_set(True)
bpy.context.view_layer.objects.active = pieces[0]
bpy.ops.object.join()
metal = bpy.context.object
metal.name = "SM_AliceBackpack_Hardware"
metal.data.name = "SM_AliceBackpack_Hardware"
bm = bmesh.new(); bm.from_mesh(metal.data)
tiny = [f for f in bm.faces if f.calc_area() < 1e-13]
if tiny: bmesh.ops.delete(bm, geom=tiny, context="FACES")
bm.to_mesh(metal.data); bm.free(); metal.data.update()

# All faces of this object are metal; collapse to one material slot before the
# final join so no empty slots can break the OBJ exporter.
metal_mat = low.data.materials[3]
metal.data.materials.clear()
metal.data.materials.append(metal_mat)
for p in metal.data.polygons:
    p.material_index = 0

layer = metal.data.uv_layers.active

# Pass 1: nearest good loop.  Pass 2+: copy a complete good UV triangle for any
# face that still cannot form area.  Both keep the hardware inside its atlas.
from mathutils import kdtree
for pass_i in range(3):
    bad_faces = [p for p in metal.data.polygons if poly_uv_area(layer, p) < 1e-10]
    if not bad_faces:
        break
    good = [p for p in metal.data.polygons if poly_uv_area(layer, p) >= 1e-10]
    if not good:
        break
    coords, uvs = [], []
    for p in good:
        for li in p.loop_indices:
            coords.append(metal.data.vertices[metal.data.loops[li].vertex_index].co)
            uvs.append(tuple(layer.data[li].uv))
    kd = kdtree.KDTree(len(coords))
    for i, co in enumerate(coords): kd.insert(co, i)
    kd.balance()
    for p in bad_faces:
        for li in p.loop_indices:
            co = metal.data.vertices[metal.data.loops[li].vertex_index].co
            _, idx, _ = kd.find(co)
            layer.data[li].uv = uvs[idx]
    print("BUCKLE_UV_LOOP", pass_i, "bad_before", len(bad_faces))

bad_faces = [p for p in metal.data.polygons if poly_uv_area(layer, p) < 1e-10]
if bad_faces:
    good = [p for p in metal.data.polygons if poly_uv_area(layer, p) >= 1e-10]
    centers = []
    for p in good:
        vs = [metal.data.vertices[metal.data.loops[li].vertex_index].co for li in p.loop_indices]
        centers.append(sum(vs, Vector()) / len(vs))
    kd = kdtree.KDTree(len(centers))
    for i, co in enumerate(centers): kd.insert(co, i)
    kd.balance()
    for p in bad_faces:
        co = sum((metal.data.vertices[metal.data.loops[li].vertex_index].co for li in p.loop_indices), Vector()) / len(p.loop_indices)
        _, idx, _ = kd.find(co)
        gp = good[idx]
        guv = [tuple(layer.data[li].uv) for li in gp.loop_indices]
        for k, li in enumerate(p.loop_indices):
            layer.data[li].uv = guv[k % len(guv)]
    print("BUCKLE_UV_FACE_FALLBACK", len(bad_faces))

bad_final = sum(1 for p in metal.data.polygons if poly_uv_area(layer, p) < 1e-10)
print("BUCKLE_METAL faces", len(metal.data.polygons), "bad_uv", bad_final)

# Replace the old hardware in the final mesh.
for o in bpy.context.selected_objects: o.select_set(False)
low.select_set(True); bpy.context.view_layer.objects.active = low
bm = bmesh.new(); bm.from_mesh(low.data)
old_metal = [f for f in bm.faces if f.material_index == 3]
bmesh.ops.delete(bm, geom=old_metal, context="FACES")
bm.to_mesh(low.data); bm.free(); low.data.update()
bpy.ops.object.select_all(action="DESELECT")
low.select_set(True); metal.select_set(True)
bpy.context.view_layer.objects.active = low
bpy.ops.object.join()
final = bpy.context.object
final.name = "SM_AliceBackpack"
final.data.name = "SM_AliceBackpack"
final.data.update()
print("BUCKLE_FINAL verts", len(final.data.vertices), "faces", len(final.data.polygons),
      "materials", [m.name if m else None for m in final.data.materials])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv_bevel.blend"))
print("BUCKLE_FINAL saved")