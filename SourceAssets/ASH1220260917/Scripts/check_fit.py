"""Report the fitted gun's real placement at idle frame 0.

Run: blender --background --factory-startup --python-exit-code 1 --python check_fit.py
"""
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

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
dg = bpy.context.evaluated_depsgraph_get()

ev = gun.evaluated_get(dg)
me = ev.to_mesh()
pts = [ev.matrix_world @ v.co for v in me.vertices]
lo = [round(min(p[i] for p in pts), 4) for i in range(3)]
hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
print("ASH12_GUN_BBOX", lo, hi, [round(hi[i] - lo[i], 4) for i in range(3)])
ev.to_mesh_clear()

for name in ("WPN_root", "WPN_SOCKET_Magazine", "WPN_Trigger", "WPN_RearSight", "WPN_FrontSight",
             "WPN_SOCKET_Muzzle", "WPN_SOCKET_Eject", "hand_r", "hand_l", "index_01_r", "index_01_l",
             "thumb_01_l", "lowerarm_l"):
    bone = rig.pose.bones[name]
    print("ASH12_BONE %-22s head=%s tail=%s" % (
        name,
        [round(float(c), 4) for c in (rig.matrix_world @ bone.head)],
        [round(float(c), 4) for c in (rig.matrix_world @ bone.tail)],
    ))

# Grip / magazine / rail regions of the fitted mesh, as the eye sees them.
for label, box in (
    ("grip", ((0.02, -0.05, -0.22), (0.09, 0.09, -0.05))),
    ("magazine", ((0.02, -0.18, -0.25), (0.09, 0.06, 0.02))),
    ("foregrip_area", ((0.02, 0.27, -0.20), (0.09, 0.41, 0.02))),
    ("carry_handle", ((0.02, -0.05, 0.0), (0.09, 0.12, 0.12))),
):
    lo_b, hi_b = box
    hit = [p for p in pts if all(lo_b[i] <= p[i] <= hi_b[i] for i in range(3))]
    if hit:
        print("ASH12_REGION %-14s n=%-6d min=%s max=%s" % (
            label, len(hit),
            [round(min(p[i] for p in hit), 4) for i in range(3)],
            [round(max(p[i] for p in hit), 4) for i in range(3)],
        ))
    else:
        print("ASH12_REGION %-14s empty" % label)
print("ASH12_CHECK_DONE")
