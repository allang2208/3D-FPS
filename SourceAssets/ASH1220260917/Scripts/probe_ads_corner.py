"""Find which GUN part reaches into the top-right corner of the ADS frame.

The arm probe cleared every arm bone from the frustum, yet a wedge still shows
at the top-right in real captures. This projects the gun mesh itself into the
ADS frustum and reports vertices in the top-right region (pitch > 10 deg,
yaw > 18 deg) grouped by material slot, so the offending part is named.

Run: blender --background --factory-startup --python-exit-code 1 --python probe_ads_corner.py
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
if not rig.animation_data:
    rig.animation_data_create()

EFFECTIVE_EYE = 0.18
VERTICAL_FOV = 55.0
ASPECT = 16.0 / 9.0

action = bpy.data.actions["ASH12_aim"]
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}

rear = pose["WPN_RearSight"].translation.copy()
front = pose["WPN_FrontSight"].translation.copy()
eye = rear - (front - rear).normalized() * EFFECTIVE_EYE
aim_axis = (front - rear).normalized()
up = (pose["WPN_root"].to_quaternion() @ Vector((0.0, 0.0, 1.0))).normalized()
right = aim_axis.cross(up).normalized()
up = right.cross(aim_axis).normalized()

import math
HORIZONTAL_HALF = math.degrees(math.atan(math.tan(math.radians(VERTICAL_FOV * 0.5)) * ASPECT))

depsgraph = bpy.context.evaluated_depsgraph_get()
gun_eval = gun.evaluated_get(depsgraph)
gun_mesh = gun_eval.to_mesh()
gun_map = gun_eval.matrix_world
root_inv = pose["WPN_root"].inverted()

hits = []
for vertex in gun_mesh.vertices:
    point = gun_map @ vertex.co
    rel = point - eye
    forward = rel.dot(aim_axis)
    if forward <= 0.01:
        continue
    pitch = math.degrees(math.atan2(rel.dot(up), forward))
    yaw = math.degrees(math.atan2(rel.dot(right), forward))
    if abs(pitch) > VERTICAL_FOV * 0.5 or abs(yaw) > HORIZONTAL_HALF:
        continue
    hits.append((pitch > 10 and yaw > 18, pitch, yaw, vertex.index, point))
gun_eval.to_mesh_clear()

corner = [h for h in hits if h[0]]
print("gun verts in frustum: %d   top-right (pitch>10,yaw>18): %d" % (len(hits), len(corner)))

# Material slot lookup through faces of the original mesh.
mesh = gun.data
slot_of_vertex = {}
for poly in mesh.polygons:
    slot = poly.material_index
    for v in poly.vertices:
        slot_of_vertex.setdefault(v, slot)
materials = [m.name for m in gun_eval.object.material_slots] if hasattr(gun_eval, "object") else []

groups = {}
for _, pitch, yaw, index, point in corner:
    slot = slot_of_vertex.get(index, -1)
    name = gun.material_slots[slot].name if 0 <= slot < len(gun.material_slots) else "?"
    g = groups.setdefault(name, [0, 1e9, -1e9, 1e9, -1e9])
    g[0] += 1
    g[1] = min(g[1], pitch); g[2] = max(g[2], pitch)
    g[3] = min(g[3], yaw); g[4] = max(g[4], yaw)
    if g[0] <= 3:
        local = root_inv @ point
        print("  %.3fm corner vert  pitch %5.1f yaw %5.1f  recv=(%.2f, %.2f, %.2f)  %s"
              % (rel_len, ) if False else
              "  corner vert pitch %5.1f yaw %5.1f  recv=(%.2f, %.2f, %.2f)  %s"
              % (pitch, yaw, local.x, local.y, local.z, name))

print("\nper-material summary in the top-right corner:")
for name, (count, plo, phi, ylo, yhi) in sorted(groups.items(), key=lambda kv: -kv[1][0]):
    print("  %-28s %4d  pitch [%5.1f..%5.1f]  yaw [%5.1f..%5.1f]"
          % (name, count, plo, phi, ylo, yhi))

# How close does the corner region come to the frame edge?
if corner:
    print("\nmax pitch %.1f (half=%.1f)  max yaw %.1f (half=%.1f)"
          % (max(h[1] for h in corner), VERTICAL_FOV * .5,
             max(h[2] for h in corner), HORIZONTAL_HALF))

print("\nASH12_ADS_CORNER_COMPLETE")
