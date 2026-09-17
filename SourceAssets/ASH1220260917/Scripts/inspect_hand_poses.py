"""Read the accepted hand poses so a fist can be authored for the bolt handle.

The firing hand keeps the M4 grip's curl, which leaves the trigger finger
extended -- wrong when the same hand is wrapped round a charging handle. This
prints the local rotations of the finger joints in two accepted poses: the grip
(with the index extended) and the support hand clamped on the handguard (a real
fist), so the joint-and-axis difference between them is explicit.

Run: blender --background --factory-startup --python-exit-code 1 --python inspect_hand_poses.py
"""
import math
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
JOINTS = ("01", "02", "03", "metacarpal")

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
if not rig.animation_data:
    rig.animation_data_create()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}


def sample(name, frame):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()


def report(label, side):
    print("\n--- %s (hand_%s) ---" % (label, side))
    print("  %-22s %-28s %s" % ("bone", "local euler XYZ (deg)", "euler minus rest"))
    for finger in FINGERS:
        for joint in JOINTS:
            name = "%s_%s_%s" % (finger, joint, side)
            if name not in rig.pose.bones:
                continue
            bone = rig.pose.bones[name]
            euler = bone.rotation_quaternion.to_euler("XYZ")
            local = bone.matrix_basis.to_euler("XYZ")
            print("  %-22s (%7.1f,%7.1f,%7.1f)   (%7.1f,%7.1f,%7.1f)"
                  % (name, math.degrees(euler.x), math.degrees(euler.y), math.degrees(euler.z),
                     math.degrees(local.x), math.degrees(local.y), math.degrees(local.z)))


sample("ASH12_idle", 0)
report("idle = M4 grip on the pistol grip", "r")
report("idle = support hand on the handguard", "l")
sample("ASH12_reload_empty", 60)
report("reload_empty f60 = support hand still on the handguard", "l")

print("\nASH12_HAND_POSES_COMPLETE")
