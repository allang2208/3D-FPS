# Procedural metal ingot (铸锭) for FPSGAME smelting — run headless:
#   "E:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b -P build_ingot_blender.py
# Exports Saved/IngotPipeline/SM_Ingot.fbx. Real-world size ~24 x 9 x 5 cm (pickup normalizes anyway).
# Shape: tapered ingot bar with a shallow double-stamped recess on top and chamfered edges.
import bpy, bmesh, os

OUT = r"D:\FPS3D\FPSGAME\Saved\IngotPipeline"
os.makedirs(OUT, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
for block in (bpy.data.meshes, bpy.data.materials):
    for b in list(block):
        if b.users == 0:
            block.remove(b)

L_BOTTOM, W_BOTTOM = 0.24, 0.09   # foot footprint (m)
L_TOP,    W_TOP    = 0.19, 0.068  # top face footprint (tapered)
H                  = 0.05         # body height

mesh = bpy.data.meshes.new("SM_Ingot")
bm = bmesh.new()

def rect(l, w, z):
    hw, hl = w * 0.5, l * 0.5
    return [bm.verts.new((-hl, -hw, z)), bm.verts.new((hl, -hw, z)),
            bm.verts.new((hl, hw, z)), bm.verts.new((-hl, hw, z))]

rb = rect(L_BOTTOM, W_BOTTOM, 0.0)
rt = rect(L_TOP, W_TOP, H)
for i in range(4):
    bm.faces.new((rb[i], rb[(i + 1) % 4], rt[(i + 1) % 4], rt[i]))   # tapered sides
bm.faces.new(list(reversed(rb)))     # bottom cap
top = bm.faces.new(rt)               # top cap

# Stamped recess: inset once and sink, then a hairline inset back up (reads as a pour stamp).
res = bmesh.ops.inset_individual(bm, faces=[top], thickness=0.016, depth=-0.005, use_even_offset=True)
try:
    bmesh.ops.inset_individual(bm, faces=res.get("faces", [top]), thickness=0.004, depth=0.0012, use_even_offset=True)
except Exception as e:
    print("second inset skipped:", e)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

# Chamfer every edge exactly once (geom list must not repeat elements).
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.0022, segments=2,
                affect='EDGES', profile=0.72, clamp_overlap=True)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)

bm.to_mesh(mesh); bm.free()
obj = bpy.data.objects.new("SM_Ingot", mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
for o in bpy.data.objects:
    o.select_set(o is obj)

for p in mesh.polygons:
    p.use_smooth = True
try:
    bpy.ops.object.shade_auto_smooth(angle=0.8726)   # 50°: smooth faces, crisp chamfers
except Exception as e:
    print("smooth-by-angle skipped:", e)

mat = bpy.data.materials.new("M_Ingot_Slot")          # name kept by the UE importer
mesh.materials.append(mat)

fbx = os.path.join(OUT, "SM_Ingot.fbx")
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                         axis_forward='-Y', axis_up='Z', path_mode='COPY', embed_textures=False)
print("EXPORTED", fbx, "verts=", len(mesh.vertices), "polys=", len(mesh.polygons))
