"""Trace the magazine socket and the support hand through the reload clips, in
the receiver's own frame, so the hand offset can be designed from data.

Run: ASH12_CLIP=reload blender --background --factory-startup --python-exit-code 1 --python probe_reload.py
"""
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
CLIP = os.environ.get("ASH12_CLIP", "reload")

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
action = bpy.data.actions["ASH12_" + CLIP]
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]

print("ASH12_TRACE_BEGIN clip=%s" % CLIP)
print("  frame   magsocket(x,y,z)            hand_l(x,y,z)             index_l(x,y,z)          dist(hand,mag)")
for frame in range(0, int(action.frame_range[1]) + 1, 4):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    root = rig.pose.bones["WPN_root"].matrix
    to_local = root.inverted()

    def local(name):
        return to_local @ rig.pose.bones[name].matrix.translation

    mag = local("WPN_SOCKET_Magazine")
    hand = local("hand_l")
    index = local("index_01_l")
    print("  %5d   %-24s %-24s %-24s %.4f" % (
        frame,
        "(%.3f,%.3f,%.3f)" % tuple(mag),
        "(%.3f,%.3f,%.3f)" % tuple(hand),
        "(%.3f,%.3f,%.3f)" % tuple(index),
        (index - mag).length,
    ))
print("ASH12_TRACE_END")
