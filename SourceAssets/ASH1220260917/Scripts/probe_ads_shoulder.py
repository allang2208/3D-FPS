"""Measure the firing-arm chain against the ADS eye before shifting it.

Prints the world positions of shoulder/elbow/hand, the ADS eye, and the
upper-arm mesh vertices that are closest to the eye, plus their angle inside
the 55-degree ADS view frustum, so a shoulder shift can be aimed at the actual
geometry instead of guessed.

Run: blender --background --factory-startup --python-exit-code 1 --python probe_ads_shoulder.py
"""
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
arms = bpy.data.objects["SK_Manny_Arms_Export"]
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

# Camera basis: looks along aim_axis, up from the receiver.
up = (pose["WPN_root"].to_quaternion() @ Vector((0.0, 0.0, 1.0))).normalized()
right = aim_axis.cross(up).normalized()
up = right.cross(aim_axis).normalized()

print("eye      %s" % ["%.3f" % v for v in eye])
for bone in ("upperarm_r", "lowerarm_r", "hand_r", "upperarm_l", "clavicle_r"):
    if bone in pose:
        print("%-11s %s" % (bone, ["%.3f" % v for v in pose[bone].translation]))

depsgraph = bpy.context.evaluated_depsgraph_get()
arms_eval = arms.evaluated_get(depsgraph)
arms_mesh = arms_eval.to_mesh()
arms_map = arms_eval.matrix_world

# Occlusion: a vertex hidden behind the gun itself cannot reach the screen,
# so the frustum count alone overstates what the player actually sees.
from mathutils.bvhtree import BVHTree
gun = bpy.data.objects["ASH12_Export"]
gun_eval = gun.evaluated_get(depsgraph)
gun_mesh = gun_eval.to_mesh()
gun_map = gun_eval.matrix_world
tree = BVHTree.FromPolygons([gun_map @ v.co for v in gun_mesh.vertices],
                            [tuple(p.vertices) for p in gun_mesh.polygons], all_triangles=False)
gun_eval.to_mesh_clear()

UPPER_GROUPS = ()  # empty = report every vertex group, not just arm bones
samples = []
for vertex in arms_mesh.vertices:
    point = arms_map @ vertex.co
    rel = point - eye
    forward = rel.dot(aim_axis)
    if forward <= 0.01:
        continue  # behind the camera plane
    pitch = __import__("math").degrees(__import__("math").atan2(rel.dot(up), forward))
    yaw = __import__("math").degrees(__import__("math").atan2(rel.dot(right), forward))
    if abs(pitch) > VERTICAL_FOV * 0.5 or abs(yaw) > __import__("math").degrees(
            __import__("math").atan(__import__("math").tan(__import__("math").radians(VERTICAL_FOV * 0.5)) * ASPECT)):
        continue  # outside the frustum
    groups = arms.data.vertices[vertex.index].groups
    owner = max(groups, key=lambda g: g.weight).group if groups else -1
    name = arms.vertex_groups[owner].name if owner >= 0 else "?"
    if UPPER_GROUPS and not any(name.startswith(g) for g in UPPER_GROUPS):
        continue
    direction = (point - eye).normalized()
    hit_location, hit_normal, hit_index, hit_dist = tree.ray_cast(eye, direction)
    if hit_location is not None and hit_dist < rel.length - 0.002:
        continue  # the gun itself hides this vertex
    samples.append((rel.length, name, point, pitch, yaw))
arms_eval.to_mesh_clear()

samples.sort()
print("\nvisible verts inside the ADS frustum: %d" % len(samples))
for dist, name, point, pitch, yaw in samples[:12]:
    print("  %6.1f mm  %-22s pitch %6.1f  yaw %6.1f  (%.3f, %.3f, %.3f)"
          % (dist * 1000, name, pitch, yaw, point.x, point.y, point.z))
groups = {}
for dist, name, point, pitch, yaw in samples:
    g = groups.setdefault(name, [0, 1e9, -1e9, 1e9, -1e9])
    g[0] += 1
    g[1] = min(g[1], pitch); g[2] = max(g[2], pitch)
    g[3] = min(g[3], yaw); g[4] = max(g[4], yaw)
print("\nper-group summary (count, pitch range, yaw range):")
for name, (count, plo, phi, ylo, yhi) in sorted(groups.items(), key=lambda kv: -kv[1][0]):
    print("  %-24s %4d  pitch [%6.1f..%6.1f]  yaw [%6.1f..%6.1f]"
          % (name, count, plo, phi, ylo, yhi))
if samples:
    worst = max(samples, key=lambda s: abs(s[4]))
    print("widest yaw %.1f deg at %.1f mm (%s)" % (worst[4], worst[0] * 1000, worst[1]))

print("\nASH12_ADS_SHOULDER_COMPLETE")
