"""Zoom-render individual connected components with the rest of the gun dimmed.

Run: ASH12_COMPONENTS="78,117" blender --background --factory-startup \
       --python-exit-code 1 --python inspect_component.py
"""
import bmesh
import bpy
import json
import math
import os

from mathutils import Vector

ROOT = r"D:\FPS3D\资产\oden先辈"
SOURCE = os.path.join(ROOT, "fbx", "weapon.FBX")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "Reference"))
WANT = [int(x) for x in os.environ.get("ASH12_COMPONENTS", "78,117").split(",") if x.strip()]
TAG = os.environ.get("ASH12_TAG", "")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SOURCE, use_custom_normals=True)
for img in bpy.data.images:
    name = os.path.basename(img.filepath.replace("\\", "/"))
    for sub in ("cdm", "natga"):
        cand = os.path.join(ROOT, sub, name)
        if name and not os.path.exists(img.filepath) and os.path.exists(cand):
            img.filepath = cand
            img.reload()
            break

src = next(o for o in bpy.context.scene.objects if o.type == "MESH")
me = src.data
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()

seen = set()
groups = []
for vert in bm.verts:
    if vert.index in seen:
        continue
    stack = [vert]
    seen.add(vert.index)
    members = []
    while stack:
        v = stack.pop()
        members.append(v.index)
        for edge in v.link_edges:
            other = edge.other_vert(v)
            if other.index not in seen:
                seen.add(other.index)
                stack.append(other)
    groups.append(members)
# Discovery order matches components.py, so component ids stay comparable.

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1.0)
for name, rot, energy in (("key", (58, 0, 40), 4.0), ("fill", (68, 0, -130), 2.0), ("rim", (105, 0, 185), 1.8)):
    lamp = bpy.data.lights.new(name, "SUN")
    lamp.energy = energy
    holder = bpy.data.objects.new(name, lamp)
    holder.rotation_euler = tuple(math.radians(a) for a in rot)
    scene.collection.objects.link(holder)
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

dim = bpy.data.materials.new("Dim")
dim.use_nodes = True
bsdf = dim.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.12, 0.12, 0.13, 1)
bsdf.inputs["Roughness"].default_value = 0.7
src.data.materials.clear()
src.data.materials.append(dim)

for cid in WANT:
    members = set(groups[cid])
    poly_ids = [p.index for p in me.polygons if all(v in members for v in p.vertices)]
    vids = sorted({v for pid in poly_ids for v in me.polygons[pid].vertices})
    new = bpy.data.meshes.new("c%d" % cid)
    remap = {old: i for i, old in enumerate(vids)}
    new.from_pydata([me.vertices[v].co.copy() for v in vids], [], [[remap[v] for v in me.polygons[pid].vertices] for pid in poly_ids])
    new.update()
    hl = bpy.data.materials.new("HL%d" % cid)
    hl.use_nodes = True
    b = hl.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.9, 0.25, 0.1, 1)
    b.inputs["Roughness"].default_value = 0.35
    new.materials.append(hl)
    obj = bpy.data.objects.new("hl%d" % cid, new)
    scene.collection.objects.link(obj)
    co = [me.vertices[i].co for i in vids]
    lo = Vector([min(c[i] for c in co) for i in range(3)])
    hi = Vector([max(c[i] for c in co) for i in range(3)])
    center = (lo + hi) / 2
    span = max(max(hi - lo), 3.0) * 4.0
    print("ASH12_COMPONENT %d verts=%d min=%s max=%s" % (cid, len(vids), [round(x, 3) for x in lo], [round(x, 3) for x in hi]))
    for view, dirv in (("negY", Vector((0, -1, 0))), ("posY", Vector((0, 1, 0))), ("posZ", Vector((0, 0, 1)))):
        cam.location = center + dirv * 200
        cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam_data.ortho_scale = span * 1.15 if view != "posZ" else span
        scene.render.filepath = os.path.join(OUT, "component_%d%s_%s.png" % (cid, TAG, view))
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj, do_unlink=True)
print("ASH12_COMPONENT_DONE")
