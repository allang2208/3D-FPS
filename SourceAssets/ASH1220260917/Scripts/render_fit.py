"""Render the fitted ASH-12 on the accepted arms for hand-fit review.

Run: ASH12_FRAMES="idle:0,reload:43" blender --background --factory-startup \
       --python-exit-code 1 --python render_fit.py
Writes Reference/fit_<clip>_<frame>_<view>.png
"""
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(O, "Reference")
FRAMES = os.environ.get("ASH12_FRAMES", "idle:0,reload:43,reload:76,reload:110,reload_empty:142")
VIEWS = os.environ.get("ASH12_VIEWS", "side,eye")

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
KEEP = ("SK_M4_Infima", "SK_Manny_Arms_Export", "ASH12_Export")
for obj in scene.objects:
    obj.hide_render = obj.name not in KEEP
for obj in list(scene.objects):
    if obj.type in ("CAMERA", "LIGHT"):
        bpy.data.objects.remove(obj, do_unlink=True)

try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("Preview")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.18, 0.21, 1.0)

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def aim(location, target):
    cam.location = location
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()


for spec in FRAMES.split(","):
    clip, frame = spec.split(":")
    frame = int(frame)
    action = bpy.data.actions["ASH12_" + clip]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(frame)
    bpy.context.view_layer.update()

    root = rig.matrix_world @ rig.pose.bones["WPN_root"].matrix
    center = Vector((0.056, 0.10, -0.06))

    for light_spec in ((1.2, -0.4, 1.2, 320), (-1.0, -0.3, 0.6, 220), (0.4, 1.2, 0.2, 140)):
        lamp = bpy.data.lights.new("area", "AREA")
        lamp.energy = light_spec[3]
        lamp.size = 1.6
        holder = bpy.data.objects.new("area", lamp)
        scene.collection.objects.link(holder)
        holder.location = center + Vector(light_spec[:3])
        holder.rotation_euler = (center - holder.location).to_track_quat("-Z", "Y").to_euler()

    for view in VIEWS.split(","):
        if view == "side":
            cam_data.type = "ORTHO"
            cam_data.ortho_scale = 0.95
            aim(center + Vector((1.6, 0.0, 0.10)), center)
        elif view == "top":
            cam_data.type = "ORTHO"
            cam_data.ortho_scale = 0.95
            aim(center + Vector((0.0, 0.0, 1.6)), center)
        elif view == "eye":
            cam_data.type = "PERSP"
            cam_data.lens = 24.0
            aim(Vector((0.058, -0.075, 0.085)), Vector((0.058, 0.60, 0.05)))
        elif view == "hold":
            cam_data.type = "PERSP"
            cam_data.lens = 35.0
            aim(Vector((0.42, -0.12, 0.16)), Vector((0.056, 0.12, -0.08)))
        elif view == "well":
            # Gun-relative so the magazine well stays framed while the reload
            # swings the rifle around.
            pose = rig.pose.bones
            well = rig.matrix_world @ pose["WPN_SOCKET_Magazine"].matrix.translation
            rear = rig.matrix_world @ pose["WPN_RearSight"].matrix.translation
            front = rig.matrix_world @ pose["WPN_FrontSight"].matrix.translation
            fwd = (front - rear).normalized()
            up = (Vector((0.0, 0.0, 1.0)) - fwd * Vector((0.0, 0.0, 1.0)).dot(fwd)).normalized()
            right = fwd.cross(up)
            cam_data.type = "PERSP"
            cam_data.lens = 35.0
            aim(well + up * 0.26 + right * 0.30 - fwd * 0.06, well)
        scene.render.filepath = os.path.join(OUT, "fit_%s_%d_%s.png" % (clip, frame, view))
        bpy.ops.render.render(write_still=True)
        print("ASH12_FIT", scene.render.filepath)

    for obj in [o for o in scene.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(obj, do_unlink=True)

print("ASH12_FIT_DONE")
