"""Diagnostic: project authored hat triangles into the saved icon camera and
report the rendered colour per material.  Does not modify assets."""
import json
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path("D:/FPS3D/FPSGAME")
SRC = ROOT / "SourceAssets/FieldHat20261019"
bpy.ops.wm.open_mainfile(filepath=str(SRC / "ue_field_hat-icon.blend"))
scene = bpy.context.scene
camera = scene.camera
obj = bpy.data.objects["FieldHat"]
d = json.loads((SRC / "Authored/hat.json").read_text(encoding="utf-8"))
icon_img = bpy.data.images.load(str(SRC / "ue_field_hat.png"), check_existing=False)
icon_img.colorspace_settings.name = "Non-Color"
buf = np.empty(len(icon_img.pixels), np.float32)
icon_img.pixels.foreach_get(buf)
height, width = icon_img.size[1], icon_img.size[0]
icon = buf.reshape(height, width, 4)[::-1]
view = camera.location.copy()
samples = {i: [] for i in range(len(d["material_slots"]))}
for fi, (tri, material) in enumerate(zip(d["triangles"], d["triangle_materials"])):
    p = np.mean([d["positions"][i] for i in tri], axis=0)
    n = np.array(d["normals"][fi][0], np.float64)
    world = obj.matrix_world @ Vector((p[0] * 0.01, -p[1] * 0.01, p[2] * 0.01))
    world_n = obj.matrix_world.to_3x3() @ Vector((n[0], -n[1], n[2]))
    if (view - world).dot(world_n) <= 0:
        continue
    co = world_to_camera_view(scene, camera, world)
    x = int(round(co.x * width))
    y = int(round((1.0 - co.y) * height))
    if 0 <= x < width and 0 <= y < height and icon[y, x, 3] > 0.9:
        samples[material].append(icon[y, x, :3])
for material, values in samples.items():
    if not values:
        print("MAT", material, d["material_slots"][material], "visible=0")
        continue
    rgb = np.array(values)
    print("MAT", material, d["material_slots"][material], "visible_px=", len(rgb),
          "mean_srgb=", (rgb.mean(0) * 255).round(1).tolist(),
          "max_srgb=", (rgb.max(0) * 255).round(1).tolist())