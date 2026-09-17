"""Render the ADS view at several eye reliefs, so the arm blob and the sight
picture can be judged together instead of argued about.

ADSRearEyeDistance is a single number doing two jobs: it sets how much of the
receiver is in frame and how deep the camera sits in the shooter's own arm. The
ship's value (0.18 m) was chosen for the framing before the arm was ever looked
at.

Run: blender --background --factory-startup --python-exit-code 1 --python render_ads_eyes.py
Writes Reference/ads_eye<cm>.png
"""
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(O, "Reference")
DISTANCES = [float(v) for v in os.environ.get("ASH12_EYES", "0.10,0.12,0.15,0.18").split(",")]

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
world.node_tree.nodes["Background"].inputs[0].default_value = (0.20, 0.22, 0.25, 1.0)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 18.0
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def aim_at(location, target):
    cam.location = location
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()


action = bpy.data.actions["ASH12_aim"]
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
rear = pose["WPN_RearSight"].translation.copy()
front = pose["WPN_FrontSight"].translation.copy()
fwd = (front - rear).normalized()

for lamp_spec in ((1.2, -0.4, 1.2, 320), (-1.0, -0.3, 0.6, 220), (0.4, 1.2, 0.2, 140)):
    lamp = bpy.data.lights.new("area", "AREA")
    lamp.energy = lamp_spec[3]
    lamp.size = 1.6
    holder = bpy.data.objects.new("area", lamp)
    scene.collection.objects.link(holder)
    holder.location = rear + Vector(lamp_spec[:3])
    holder.rotation_euler = (rear - holder.location).to_track_quat("-Z", "Y").to_euler()

for distance in DISTANCES:
    eye = rear - fwd * distance
    aim_at(eye, eye + fwd)
    scene.render.filepath = os.path.join(OUT, "ads_eye%02d.png" % int(round(distance * 100)))
    bpy.ops.render.render(write_still=True)
    print("ASH12_ADS_EYE %.2f %s" % (distance, scene.render.filepath))

print("ASH12_ADS_EYES_DONE")
