"""How far the receiver actually rolls, pitches and yaws over the reload.

The pose is authored as a rigid transform in the receiver's own frame, so the
numbers below are the only honest check that the roll reaches the reference's
magnitude and comes back to level at the ends.

Run: blender --background --factory-startup --python-exit-code 1 --python measure_roll.py
"""
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
if not rig.animation_data:
    rig.animation_data_create()


def sample(action, frame):
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


for clip, length in (("M4_HK416_reload_empty", 162), ("ASH12_reload_empty", 162), ("ASH12_reload", 126)):
    action = bpy.data.actions[clip]
    base = sample(action, 0.0)
    q0 = base["WPN_root"].to_quaternion()
    u0 = (q0 @ Vector((0.0, 0.0, 1.0))).normalized()
    x0 = (q0 @ Vector((1.0, 0.0, 0.0))).normalized()
    y0 = (q0 @ Vector((0.0, 1.0, 0.0))).normalized()
    print("\n=== %s ===" % clip)
    print("  frame  roll  tilt  yaw   mag_back  mag_down  hand_r   grip_gap  mag_gap")
    for frame in range(0, length + 1, 6):
        pose = sample(action, frame)
        q = pose["WPN_root"].to_quaternion()
        up = (q @ Vector((0.0, 0.0, 1.0))).normalized()
        lat = (q @ Vector((1.0, 0.0, 0.0))).normalized()
        v = Vector((up.dot(x0), up.dot(y0), up.dot(u0)))
        roll = math.degrees(math.atan2(v.x, v.z))
        tilt = math.degrees(math.acos(max(-1.0, min(1.0, v.z))))
        w = Vector((lat.dot(x0), lat.dot(y0), lat.dot(u0)))
        yaw = math.degrees(math.atan2(w.y, w.x))
        inv = pose["WPN_root"].inverted()
        root = pose["WPN_root"].translation
        mag = inv @ pose["WPN_SOCKET_Magazine"].translation
        socket = rig.data.bones["WPN_SOCKET_Magazine"].matrix_local.translation
        socket_local = rig.data.bones["WPN_root"].matrix_local.inverted() @ socket
        gap = mag - socket_local
        hand = inv @ pose["hand_r"].translation
        grip = inv @ pose["hand_l"].translation
        print("  %5d  %5.1f %5.1f %5.1f   (%6.3f,%6.3f)  (%6.3f,%6.3f,%6.3f)"
              % (frame, roll, tilt, yaw, gap.y, gap.z, hand.x, hand.y, hand.z))

print("\nASH12_ROLL_INSPECT_COMPLETE")
