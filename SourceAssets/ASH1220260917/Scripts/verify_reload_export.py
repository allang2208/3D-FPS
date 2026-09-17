"""Read the exported FBX back and re-measure what the clip actually ships.

The build writes A_ASH12_reload_empty.fbx; this imports that file into an empty
scene and re-measures the receiver's roll and the magazine's travel from the
file itself, so the numbers in the case record are not taken from the authoring
session.

Run: blender --background --factory-startup --python-exit-code 1 --python verify_reload_export.py
"""
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
FBX = os.path.join(O, "A_ASH12_reload_empty.fbx")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX, use_custom_normals=True)
scene = bpy.context.scene
rig = next(o for o in scene.objects if o.type == "ARMATURE")
action = rig.animation_data.action
print("ASH12_VERIFY armature=%s bones=%d action=%s frames=%.0f-%.0f"
      % (rig.name, len(rig.data.bones), action.name, action.frame_range[0], action.frame_range[1]))

scene.frame_set(0)
bpy.context.view_layer.update()
base = {b.name: b.matrix.copy() for b in rig.pose.bones}
q0 = base["WPN_root"].to_quaternion()
x0 = (q0 @ Vector((1.0, 0.0, 0.0))).normalized()
y0 = (q0 @ Vector((0.0, 1.0, 0.0))).normalized()
u0 = (q0 @ Vector((0.0, 0.0, 1.0))).normalized()
socket0 = base["WPN_SOCKET_Magazine"].translation.copy()

print("  frame  roll   mag back/down (m)   bolt back (m)   handle back (m)")
for frame in range(0, 163, 6):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    q = pose["WPN_root"].to_quaternion()
    up = (q @ Vector((0.0, 0.0, 1.0))).normalized()
    v = Vector((up.dot(x0), up.dot(y0), up.dot(u0)))
    roll = math.degrees(math.atan2(v.x, v.z))
    inv = pose["WPN_root"].inverted()
    mag = (inv @ pose["WPN_SOCKET_Magazine"].translation) - (inv @ socket0)
    bolt = inv @ pose["WPN_bolt"].translation
    handle = inv @ pose["WPN_ChargingHandle"].translation
    print("  %5d  %5.1f   (%6.3f,%6.3f)      %6.3f          %6.3f"
          % (frame, roll, mag.y, mag.z, bolt.y, handle.y))

print("\nASH12_VERIFY_COMPLETE")
