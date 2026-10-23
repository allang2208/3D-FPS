import bpy
import bmesh
import json
import math
import os
from mathutils import Matrix, Vector

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv.blend"))
low = next(o for o in bpy.context.scene.objects if o.type == "MESH")
print("ALICE_HIGH low", len(low.data.vertices), len(low.data.polygons))

with open(os.path.join(ROOT, "stitch_segments_3d.json"), encoding="utf-8") as f:
    seams = json.load(f)

# Unit sphere template for thread dashes.
tmp = bmesh.new()
bmesh.ops.create_uvsphere(tmp, u_segments=8, v_segments=5, radius=1.0)
tmp.verts.ensure_lookup_table()
tmp.faces.ensure_lookup_table()
tv = [v.co.copy() for v in tmp.verts]
tf = [[v.index for v in f.verts] for f in tmp.faces]
tmp.free()

verts = []
faces = []
dash_n = 0
for mat, segs in seams.items():
    for s in segs:
        p1 = Vector(s["p1"])
        p2 = Vector(s["p2"])
        n = Vector(s["n"]).normalized()
        d = p2 - p1
        length = d.length
        if length < 1e-5:
            continue
        d.normalize()
        perp = n.cross(d)
        if perp.length < 1e-6:
            continue
        perp.normalize()
        count = max(1, int(length / 0.0035))
        for i in range(count):
            t = (i + 0.5) / count
            base = p1 + d * (t * length) + n * 0.00022
            for row in (-1.0, 1.0):
                center = base + perp * (0.0011 * row)
                # Thread dash half-size: 1.6 mm long, 0.55 mm wide, 0.45 mm high.
                basis = Matrix((
                    (d.x * 0.0016, perp.x * 0.00055, n.x * 0.00045),
                    (d.y * 0.0016, perp.y * 0.00055, n.y * 0.00045),
                    (d.z * 0.0016, perp.z * 0.00055, n.z * 0.00045),
                ))
                off = len(verts)
                for v in tv:
                    co = center + basis @ v
                    verts.append((co.x, co.y, co.z))
                for f in tf:
                    faces.append([off + idx for idx in f])
                dash_n += 1
print("ALICE_HIGH dashes", dash_n, "stitch_verts", len(verts), "stitch_faces", len(faces))

# The final high-poly object contains the exact low-poly surface plus the
# raised stitch dashes.  A high-poly bevel on this mesh is intentionally not
# used: the source has many sub-millimetre edges and Blender's bevel produces
# thousands of degenerate faces, which would poison the bake.
high = low.copy()
high.data = low.data.copy()
bpy.context.collection.objects.link(high)
for o in bpy.context.selected_objects:
    o.select_set(False)
high.select_set(True)
bpy.context.view_layer.objects.active = high
high.name = "SM_AliceBackpack_High"

stitch = bpy.data.objects.new("SM_StitchHigh", bpy.data.meshes.new("SM_StitchHigh"))
bpy.context.collection.objects.link(stitch)
stitch.data.from_pydata(verts, [], faces)
stitch.data.validate(verbose=False)
for p in stitch.data.polygons:
    p.use_smooth = True
stitch.data.update()

bpy.ops.object.select_all(action="DESELECT")
high.select_set(True)
stitch.select_set(True)
bpy.context.view_layer.objects.active = high
bpy.ops.object.join()
high = bpy.context.object
high.name = "SM_AliceBackpack_High"
for p in high.data.polygons:
    p.use_smooth = True
high.data.update()

print("ALICE_HIGH final verts", len(high.data.vertices), "faces", len(high.data.polygons))
print("ALICE_HIGH dimensions", tuple(round(v, 4) for v in high.dimensions))
bpy.data.objects.remove(low, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_highpoly.blend"))
print("ALICE_HIGH saved")
