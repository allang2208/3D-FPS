"""Fourth pass: where the magazine actually is, frame by frame, in the shipped clips.

Run: blender --background --factory-startup --python-exit-code 1 --python inspect_mag_track.py
"""
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
if not rig.animation_data:
    rig.animation_data_create()
print("actions with slots:")
for name in ("ASH12_reload_empty", "M4_HK416_reload_empty", "ASH12_idle"):
    a = bpy.data.actions[name]
    print("  %-24s slots=%d fcurves=%d" % (name, len(a.slots), sum(1 for _ in (a.fcurves if not a.layers else []))))


def sample(action, frame):
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


for clip, length, step in (("ASH12_reload_empty", 162, 6), ("ASH12_idle", 180, 30)):
    action = bpy.data.actions[clip]
    print("\n=== %s : magazine bone world position (receiver frame) ===" % clip)
    for frame in range(0, length + 1, step):
        pose = sample(action, frame)
        inv = pose["WPN_root"].inverted()
        m = inv @ pose["WPN_SOCKET_Magazine"].translation
        bolt = inv @ pose["WPN_bolt"].translation
        ch = inv @ pose["WPN_ChargingHandle"].translation
        hand_r = inv @ pose["hand_r"].translation
        print("  f=%3d  mag=(%6.3f,%6.3f,%6.3f)  bolt=(%6.3f,%6.3f,%6.3f)  handle=(%6.3f,%6.3f,%6.3f)  hand_r=(%6.3f,%6.3f,%6.3f)"
              % (frame, m.x, m.y, m.z, bolt.x, bolt.y, bolt.z, ch.x, ch.y, ch.z, hand_r.x, hand_r.y, hand_r.z))

print("\nASH12_MAGTRACK_INSPECT_COMPLETE")
