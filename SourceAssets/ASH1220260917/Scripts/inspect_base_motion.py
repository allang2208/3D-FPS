"""Third pass: what the accepted M4 clips actually move on the weapon bones.

Run: blender --background --factory-startup --python-exit-code 1 --python inspect_base_motion.py
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


def euler_delta(base_q, q):
    """Pitch/yaw/roll of q relative to base_q, in the base frame's own axes."""
    d = base_q.inverted() @ q
    e = d.to_euler("ZYX")
    return math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)


for clip, length in (("M4_HK416_reload_empty", 162), ("M4_HK416_reload", 126), ("M4_idle", 180)):
    action = bpy.data.actions[clip]
    first = sample(action, 0)
    q0 = first["WPN_root"].to_quaternion()
    print("\n=== %s ===" % clip)
    print("  frame   magloc(local)                magrot(deg)     root dPitch dYaw dRoll  dY(back) dZ(down)")
    for frame in range(0, length + 1, 6):
        pose = sample(action, frame)
        mag = rig.pose.bones["WPN_SOCKET_Magazine"]
        loc = mag.location
        rot = [math.degrees(a) for a in mag.rotation_quaternion.to_euler("XYZ")]
        root = pose["WPN_root"]
        p, y, r = euler_delta(q0, root.to_quaternion())
        d = root.translation - first["WPN_root"].translation
        print("  %5d   (%7.4f,%7.4f,%7.4f)  (%6.1f,%6.1f,%6.1f)  %6.1f %6.1f %6.1f  %7.4f %7.4f"
              % (frame, loc.x, loc.y, loc.z, rot[0], rot[1], rot[2], p, y, r, d.y, d.z))

print("\n=== hand_r relative to the grip (receiver frame) over the empty reload ===")
action = bpy.data.actions["M4_HK416_reload_empty"]
for frame in range(0, 163, 12):
    pose = sample(action, frame)
    inv = pose["WPN_root"].inverted()
    r = inv @ pose["hand_r"].translation
    l = inv @ pose["hand_l"].translation
    print("  f=%3d hand_r=(%6.3f,%6.3f,%6.3f)  hand_l=(%6.3f,%6.3f,%6.3f)" % (frame, r.x, r.y, r.z, l.x, l.y, l.z))

print("\nASH12_BASEMOTION_INSPECT_COMPLETE")
