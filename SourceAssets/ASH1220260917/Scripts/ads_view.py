"""Reproduce what the player sees in hip and in ADS.

ADS in game places the rear-sight marker 12 cm in front of the eye on the camera
axis and turns the sight axis onto camera forward, so the same camera can be
built here from the posed markers.

Run: blender --background --factory-startup --python-exit-code 1 --python ads_view.py
"""
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(O, "Reference")

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
for obj in scene.objects:
    try:
        if obj.type == "MESH":
            obj.hide_render = obj.name != "ASH12_Export"
        elif obj.type == "LIGHT":
            obj.hide_render = True
    except ReferenceError:
        continue

try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
world = bpy.data.worlds.new("Preview")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.18, 0.20, 0.23, 1.0)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "PERSP"
cam_data.lens = 18.0
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def aim(location, target, up):
    cam.location = location
    direction = (Vector(target) - Vector(location)).normalized()
    z = -direction
    x = up.cross(z).normalized()
    y = z.cross(x).normalized()
    from mathutils import Matrix
    cam.matrix_world = Matrix(((x.x, y.x, z.x, location[0]), (x.y, y.y, z.y, location[1]), (x.z, y.z, z.z, location[2]), (0, 0, 0, 1)))


for clip, frames in (("aim", [0]), ("idle", [0])):
    action = bpy.data.actions["ASH12_" + clip]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        rear = rig.matrix_world @ rig.pose.bones["WPN_RearSight"].matrix.translation
        front = rig.matrix_world @ rig.pose.bones["WPN_FrontSight"].matrix.translation
        muzzle = rig.matrix_world @ rig.pose.bones["WPN_SOCKET_Muzzle"].matrix.translation
        root = rig.matrix_world @ rig.pose.bones["WPN_root"].matrix.translation
        axis = (front - rear).normalized()
        bore = (muzzle - root).normalized()
        yaw = math.degrees(math.atan2(axis.x, axis.y) - math.atan2(bore.x, bore.y))
        pitch = math.degrees(math.asin(axis.z) - math.asin(bore.z))
        print("ASH12_AXIS %s f%d sight_axis=(%.4f,%.4f,%.4f) bore=(%.4f,%.4f,%.4f) yaw_err=%.2f deg pitch_err=%.2f deg"
              % (clip, frame, axis.x, axis.y, axis.z, bore.x, bore.y, bore.z, yaw, pitch))

        eye = rear - axis * 0.12
        target = eye + axis
        for name, loc, tgt, up in (
            ("ads", eye, target, Vector((0.0, 0.0, 1.0))),
            ("hip", Vector((0.058, -0.075, 0.085)), Vector((0.058, 0.60, 0.05)), Vector((0.0, 0.0, 1.0))),
        ):
            aim(loc, tgt, up)
            scene.render.filepath = os.path.join(OUT, "view_%s_%s_%d.png" % (name, clip, frame))
            bpy.ops.render.render(write_still=True)
            print("ASH12_VIEW", scene.render.filepath)
print("ASH12_ADS_DONE")
