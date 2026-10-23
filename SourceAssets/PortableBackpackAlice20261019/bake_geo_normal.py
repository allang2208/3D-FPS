import bpy
import bmesh
import json
import os

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
LOW_BLEND = os.path.join(ROOT, "AliceBackpack_uv.blend")
HIGH_BLEND = os.path.join(ROOT, "AliceBackpack_highpoly.blend")
OUT_DIR = os.path.join(ROOT, "Textures", "GeoNormal")
os.makedirs(OUT_DIR, exist_ok=True)
MATS = ["Canvas", "Webbing", "Leather", "Metal"]
RES = {"Canvas": 4096, "Webbing": 4096, "Leather": 4096, "Metal": 4096}
ONLY = os.environ.get("ALICE_BAKE_ONLY", "")
if os.environ.get("ALICE_BAKE_TEST"):
    RES = {m: 512 for m in MATS}

bpy.ops.wm.open_mainfile(filepath=LOW_BLEND)
low_src = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "SM_AliceBackpack")
with bpy.data.libraries.load(HIGH_BLEND, link=False) as (data_from, data_to):
    data_to.objects = [name for name in data_from.objects if name == "SM_AliceBackpack_High"]
high = data_to.objects[0]
bpy.context.collection.objects.link(high)
for o in bpy.context.scene.objects:
    o.hide_render = False

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 1
scene.render.bake.margin = 16
scene.render.bake.use_clear = True

print("ALICE_GEO_BAKE high", len(high.data.vertices), len(high.data.polygons))

for mat_name in MATS:
    if ONLY and mat_name != ONLY:
        continue
    res = RES[mat_name]
    # Isolated low-poly bake target for this material.
    low = low_src.copy()
    low.data = low_src.data.copy()
    bpy.context.collection.objects.link(low)
    low.name = "BakeLow_" + mat_name
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bm = bmesh.new()
    bm.from_mesh(low.data)
    mi = MATS.index(mat_name)
    bad = [f for f in bm.faces if f.material_index != mi]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
                # Assign all remaining faces to one slot below.
    bm.to_mesh(low.data)
    bm.free()
    low.data.update()
    low.data.materials.clear()

    bake_mat = bpy.data.materials.new("BakeMat_" + mat_name)
    bake_mat.use_nodes = True
    nt = bake_mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.new(
        "T_Alice_%s_GeoNormal" % mat_name,
        width=res, height=res, alpha=False, float_buffer=False,
    )
    img.colorspace_settings.name = "Non-Color"
    tex.image = img
    nt.nodes.active = tex
    low.data.materials.append(bake_mat)
    for p in low.data.polygons:
        p.material_index = 0

    # Select high then low; active must be low for selected-to-active.
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    print("ALICE_GEO_BAKE start", mat_name, res, "faces", len(low.data.polygons))
    bpy.ops.object.bake(
        type="NORMAL",
        normal_space="TANGENT",
        use_selected_to_active=True,
        cage_extrusion=0.002,
        max_ray_distance=0.01,
        margin=16,
        use_clear=True,
    )
    path = os.path.join(OUT_DIR, "T_Alice_%s_GeoNormal.png" % mat_name)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    print("ALICE_GEO_BAKE saved", path)
    bpy.data.objects.remove(low, do_unlink=True)

print("ALICE_GEO_BAKE done")
