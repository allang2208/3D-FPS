"""Relink the oden textures, split the single mesh into one object per material,
report bounds, and render an overview plus one isolated render per part.

Run: blender --background --factory-startup --python-exit-code 1 --python split_parts.py
"""
import json
import math
import os

import bpy
from mathutils import Vector

ROOT = r"D:\FPS3D\资产\oden先辈"
SOURCE = os.path.join(ROOT, "fbx", "weapon.FBX")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "Reference"))
PARTS_DIR = os.path.join(OUT, "parts")
RES = 1200

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SOURCE, use_custom_normals=True)


def relink():
    fixed = {}
    for img in bpy.data.images:
        name = os.path.basename(img.filepath.replace("\\", "/"))
        if not name or os.path.exists(img.filepath):
            continue
        for sub in ("cdm", "natga"):
            cand = os.path.join(ROOT, sub, name)
            if os.path.exists(cand):
                img.filepath = cand
                img.reload()
                fixed[name] = cand
                break
    return fixed


fixed = relink()
print("ASH12_RELINKED", len(fixed))

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
src = meshes[0]
me = src.data
parts = []
for slot_idx, mat in enumerate(me.materials):
    poly_ids = [p.index for p in me.polygons if p.material_index == slot_idx]
    if not poly_ids:
        continue
    vids = sorted({v for pid in poly_ids for v in me.polygons[pid].vertices})
    new = bpy.data.meshes.new("part_%s" % mat.name.split(" ")[0])
    remap = {old: new_i for new_i, old in enumerate(vids)}
    new.from_pydata([me.vertices[v].co.copy() for v in vids], [], [[remap[v] for v in me.polygons[pid].vertices] for pid in poly_ids])
    new.update()
    for uv in me.uv_layers:
        layer = new.uv_layers.new(name=uv.name)
        for new_poly, pid in zip(new.polygons, poly_ids):
            for k, li in enumerate(me.polygons[pid].loop_indices):
                layer.data[new_poly.loop_start + k].uv = uv.data[li].uv
    new.materials.append(mat)
    obj = bpy.data.objects.new("part_%s" % mat.name.split(" ")[0], new)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = src
    lo = [min(v.co[i] for v in new.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in new.vertices) for i in range(3)]
    tex = []
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                tex.append(os.path.basename(node.image.filepath.replace("\\", "/")))
    parts.append({
        "object": obj.name,
        "material": mat.name,
        "slot": slot_idx,
        "texture": tex,
        "vertices": len(new.vertices),
        "polygons": len(new.polygons),
        "bbox_min": [round(float(c), 4) for c in lo],
        "bbox_max": [round(float(c), 4) for c in hi],
        "center": [round(float((lo[i] + hi[i]) / 2), 4) for i in range(3)],
        "size": [round(float(hi[i] - lo[i]), 4) for i in range(3)],
    })

src.hide_render = True
lo = Vector([min(p["bbox_min"][i] for p in parts) for i in range(3)])
hi = Vector([max(p["bbox_max"][i] for p in parts) for i in range(3)])
center = (lo + hi) / 2
size = hi - lo

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = RES
scene.render.resolution_y = max(1, int(round(RES * size.z / size.x)))
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.07, 0.07, 0.08, 1.0)
for name, rot, energy in (("key", (58, 0, 40), 3.5), ("fill", (68, 0, -130), 1.8), ("rim", (105, 0, 185), 1.5)):
    lamp = bpy.data.lights.new(name, "SUN")
    lamp.energy = energy
    holder = bpy.data.objects.new(name, lamp)
    holder.rotation_euler = tuple(math.radians(a) for a in rot)
    scene.collection.objects.link(holder)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = size.x * 1.06
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = center + Vector((0, -1, 0)) * (size.x * 2)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

os.makedirs(PARTS_DIR, exist_ok=True)
scene.render.filepath = os.path.join(OUT, "parts_overview.png")
bpy.ops.render.render(write_still=True)

for entry in parts:
    for other in parts:
        bpy.data.objects[other["object"]].hide_render = other["object"] != entry["object"]
    scene.render.filepath = os.path.join(PARTS_DIR, "%s.png" % entry["object"])
    bpy.ops.render.render(write_still=True)
for entry in parts:
    bpy.data.objects[entry["object"]].hide_render = False

with open(os.path.join(OUT, "parts.json"), "w", encoding="utf-8") as fh:
    json.dump({"parts": parts, "bbox_min": list(lo), "bbox_max": list(hi), "size": list(size)}, fh, ensure_ascii=False, indent=1)

print("ASH12_PARTS_BEGIN")
print(json.dumps(parts, ensure_ascii=False, indent=1))
print("ASH12_PARTS_END")
