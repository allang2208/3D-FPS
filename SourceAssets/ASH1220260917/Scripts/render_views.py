"""Orthographic reference views of the oden source mesh.

Run: blender --background --factory-startup --python-exit-code 1 --python render_views.py
Writes Reference/view_<name><TAG>.png ; set ASH12_VIEW_TAG to suffix the files.
Set ASH12_SOURCE to override the FBX path.
"""
import math
import os

import bpy
from mathutils import Vector

SOURCE = os.environ.get("ASH12_SOURCE", r"D:\FPS3D\资产\oden先辈\fbx\weapon.FBX")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "Reference"))
TAG = os.environ.get("ASH12_VIEW_TAG", "")
RES = 1400

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SOURCE, use_custom_normals=True)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
lo = Vector([min(min((o.matrix_world @ v.co)[i] for v in o.data.vertices) for o in meshes) for i in range(3)])
hi = Vector([max(max((o.matrix_world @ v.co)[i] for v in o.data.vertices) for o in meshes) for i in range(3)])
center = (lo + hi) / 2.0
size = hi - lo

print("ASH12_MATERIALS_BEGIN")
for obj in meshes:
    for idx, mat in enumerate(obj.data.materials):
        tex = []
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    tex.append(os.path.basename(node.image.filepath.replace("\\", "/")))
        print("  slot %-3d %-16s -> %s" % (idx, mat.name if mat else "-", tex))
print("ASH12_MATERIALS_END")

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = RES
scene.render.resolution_y = max(1, int(round(RES * size.z / max(size.x, 1e-6))))
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1.0)

for name, rot, energy in (
    ("key", (55, 0, 35), 4.0),
    ("fill", (65, 0, -135), 1.6),
    ("rim", (110, 0, 180), 1.6),
):
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

# direction = unit vector pointing from the gun toward the camera.
views = {
    "right": Vector((0, -1, 0)),
    "left": Vector((0, 1, 0)),
    "top": Vector((0, 0, 1)),
    "front": Vector((-1, 0, 0)),
}

os.makedirs(OUT, exist_ok=True)
for name, dirv in views.items():
    cam.location = center + dirv * (max(size) * 2.0)
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    if name in ("right", "left"):
        cam_data.ortho_scale = size.x * 1.08
    elif name == "top":
        cam_data.ortho_scale = size.x * 1.08
    else:
        cam_data.ortho_scale = size.z * 1.08
    scene.render.filepath = os.path.join(OUT, "view_%s%s.png" % (name, TAG))
    bpy.ops.render.render(write_still=True)
    print("ASH12_RENDER", scene.render.filepath)

print("ASH12_BBOX", list(lo), list(hi))
