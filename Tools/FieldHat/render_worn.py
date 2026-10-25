"""Render a fit-check bust of the field boonie on the captured Jason head."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path("D:/FPS3D/FPSGAME")
SRC = ROOT / "SourceAssets/FieldHat20261019"
sys.path.insert(0, str(ROOT / "Tools/FieldHat"))
from author_boonie import make_materials  # noqa: E402

head = json.loads((SRC / "native_head_jason.json").read_text(encoding="utf-8"))
hat = json.loads((SRC / "Authored/hat.json").read_text(encoding="utf-8"))
hp = np.array(head["positions"])
z0 = float(hp[:, 2].max()) - 7.2
sample = hp[(hp[:, 2] > z0 - 1.5) & (hp[:, 2] < z0 + 1.5)]
center = (sample.min(0) + sample.max(0)) * 0.5
center[2] = z0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

skin = bpy.data.materials.new("PreviewSkin")
skin.use_nodes = True
bsdf = skin.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.46, 0.30, 0.23, 1.0)
bsdf.inputs["Roughness"].default_value = 0.56

head_mesh = bpy.data.meshes.new("JasonHead")
head_mesh.from_pydata([(x * 0.01, -y * 0.01, z * 0.01) for x, y, z in hp], [], head["triangles"])
head_mesh.validate()
head_mesh.update()
head_obj = bpy.data.objects.new("JasonHead", head_mesh)
scene.collection.objects.link(head_obj)
head_mesh.materials.append(skin)
for poly in head_mesh.polygons:
    poly.use_smooth = True
bpy.context.view_layer.objects.active = head_obj
head_obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
head_obj.select_set(False)

hat_mesh = bpy.data.meshes.new("FieldHatPreview")
hat_mesh.from_pydata([(x * 0.01, -y * 0.01, z * 0.01) for x, y, z in hat["positions"]], [], hat["triangles"])
hat_mesh.update()
hat_obj = bpy.data.objects.new("FieldHatPreview", hat_mesh)
scene.collection.objects.link(hat_obj)
for material in make_materials():
    hat_mesh.materials.append(material)
uv = hat_mesh.uv_layers.new(name="PhysicalGarmentUV")
for fi, poly in enumerate(hat_mesh.polygons):
    poly.material_index = hat["triangle_materials"][fi]
    poly.use_smooth = True
    for ci, li in enumerate(poly.loop_indices):
        a, b = hat["uv"][fi][ci]
        uv.data[li].uv = (a, 1.0 - b)
hat_mesh.normals_split_custom_set([(x, -y, z) for row in hat["normals"] for x, y, z in row])
hat_obj.location = (center[0] * 0.01, -center[1] * 0.01, center[2] * 0.01)
bpy.context.view_layer.update()

coords = []
for obj in (head_obj, hat_obj):
    coords.extend([obj.matrix_world @ v.co for v in obj.data.vertices])
coords = np.array([tuple(v) for v in coords])
bcenter = Vector((coords.min(0) + coords.max(0)) * 0.5)
span = float(np.max(coords.max(0) - coords.min(0)))
cam_data = bpy.data.cameras.new("PreviewCamera")
cam_data.lens = 70
cam = bpy.data.objects.new("PreviewCamera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = bcenter + Vector((0.55, 2.6, 0.38)).normalized() * span * 2.2
cam.rotation_euler = (bcenter - cam.location).to_track_quat("-Z", "Y").to_euler()
for name, offset, power, size in (("Key", (-0.8, 0.7, 1.5), 55.0, 1.2),
                                  ("Fill", (0.9, 0.2, 1.0), 18.0, 1.5),
                                  ("Rim", (0.2, 1.0, -0.6), 30.0, 0.8)):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = power * span * span
    light.size = size * span
    lamp = bpy.data.objects.new(name, light)
    scene.collection.objects.link(lamp)
    lamp.location = bcenter + Vector(offset) * span
    lamp.rotation_euler = (bcenter - lamp.location).to_track_quat("-Z", "Y").to_euler()
world = bpy.data.worlds.new("PreviewWorld")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.025, 0.028, 0.032, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.world = world
scene.render.engine = "CYCLES"
scene.cycles.samples = 192
scene.cycles.use_denoising = True
scene.cycles.adaptive_threshold = 0.005
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.render.filepath = str(SRC / "Design/worn-preview.png")
bpy.ops.render.render(write_still=True)
print("WORN_PREVIEW_SAVED", span, bcenter[:], flush=True)
