"""Render the ASH-12 inventory icon from the fitted mesh, matching the existing
weapon icon framing (side view, muzzle left, transparent, 512x256).

Run: blender --background --factory-startup --python-exit-code 1 --python render_icon.py
"""
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
OUT = r"D:\FPS3D\FPSGAME\Content\ColdSteelData\Icons\ue_ash12.png"

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
gun = bpy.data.objects["ASH12_Export"]
action = bpy.data.actions["ASH12_idle"]
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()

# The source blend links its own rigs, so objects are hidden instead of removed.
for obj in list(scene.objects):
    try:
        if obj.type == "MESH":
            obj.hide_render = obj.name != "ASH12_Export"
        elif obj.type == "LIGHT":
            obj.hide_render = True
    except ReferenceError:
        continue
gun = bpy.data.objects["ASH12_Export"]
gun.hide_render = False

try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x = 512
scene.render.resolution_y = 256
scene.render.film_transparent = True
scene.render.image_settings.color_mode = "RGBA"
world = bpy.data.worlds.new("Icon")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.34, 0.36, 0.40, 1.0)

dg = bpy.context.evaluated_depsgraph_get()
ev = gun.evaluated_get(dg)
mesh = ev.to_mesh()
points = [ev.matrix_world @ v.co for v in mesh.vertices]
lo = Vector([min(p[i] for p in points) for i in range(3)])
hi = Vector([max(p[i] for p in points) for i in range(3)])
ev.to_mesh_clear()
center = (lo + hi) / 2
size = hi - lo

# Existing inventory icons look at the left side of the gun with the muzzle to
# the left of frame; the long axis is the gun's Y, so that drives the framing.
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = size.y * 1.12
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = center + Vector((-1.6, 0.0, 0.0))
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

for offset, energy, size_w in (((1.1, -0.4, 1.0), 55, 1.4), ((-0.9, -0.3, 0.5), 35, 1.6), ((0.6, 1.1, 0.3), 45, 1.2)):
    lamp = bpy.data.lights.new("area", "AREA")
    lamp.energy = energy
    lamp.size = size_w
    holder = bpy.data.objects.new("area", lamp)
    scene.collection.objects.link(holder)
    holder.location = center + Vector(offset)
    holder.rotation_euler = (center - holder.location).to_track_quat("-Z", "Y").to_euler()

os.makedirs(os.path.dirname(OUT), exist_ok=True)
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("ASH12_ICON", OUT)
