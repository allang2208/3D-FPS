"""Name the part the ADS near clip plane slices at the top-right.

The frustum probes report nothing at the top-right, yet captures show a
grey-blue wedge with straight edges there. Straight edges + a wedge whose
apex points into the frame is what the 1 cm near plane does to geometry that
straddles it: those vertices sit at tiny forward distances, so their pitch /
yaw explode far beyond the frustum half-angles and every cone filter drops
them. This scans arms and gun for vertices just in front of the eye
(5..80 mm along the sight axis) in the upper-right quadrant and groups them
by material / vertex group, so the sliced part is named.

Run: blender --background --factory-startup --python-exit-code 1 --python probe_ads_nearplane.py
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

action = bpy.data.actions["ASH12_aim"]
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}

rear = pose["WPN_RearSight"].translation.copy()
front = pose["WPN_FrontSight"].translation.copy()
eye = rear - (front - rear).normalized() * 0.18
axis = (front - rear).normalized()
up = (pose["WPN_root"].to_quaternion() @ Vector((0.0, 0.0, 1.0))).normalized()
right = axis.cross(up).normalized()
up = right.cross(axis).normalized()
print("eye %s" % ["%.3f" % v for v in eye])

depsgraph = bpy.context.evaluated_depsgraph_get()


def scan(obj, label, group_of):
    ev = obj.evaluated_get(depsgraph)
    me = ev.to_mesh()
    mp = ev.matrix_world
    groups = {}
    for v in me.vertices:
        p = mp @ v.co
        rel = p - eye
        fwd = rel.dot(axis)
        if not (0.005 <= fwd <= 0.08):
            continue
        pitch = math.degrees(math.atan2(rel.dot(up), fwd))
        yaw = math.degrees(math.atan2(rel.dot(right), fwd))
        if pitch <= 2 or yaw <= 2:
            continue
        name = group_of(v.index)
        g = groups.setdefault(name, [0, 1e9, -1e9, 1e9, -1e9, 1e9, -1e9])
        g[0] += 1
        g[1] = min(g[1], pitch); g[2] = max(g[2], pitch)
        g[3] = min(g[3], yaw); g[4] = max(g[4], yaw)
        g[5] = min(g[5], fwd); g[6] = max(g[6], fwd)
    ev.to_mesh_clear()
    print("\n%s" % label)
    for name, (n, plo, phi, ylo, yhi, flo, fhi) in sorted(groups.items(), key=lambda kv: -kv[1][0]):
        print("  %-30s %4d  pitch[%6.1f..%6.1f] yaw[%6.1f..%6.1f] fwd[%4.1f..%4.1f]cm"
              % (name, n, plo, phi, ylo, yhi, flo * 100, fhi * 100))


arms = bpy.data.objects["SK_Manny_Arms_Export"]


def arms_group(i):
    g = arms.data.vertices[i].groups
    if g:
        return arms.vertex_groups[max(g, key=lambda x: x.weight).group].name
    return "?"


scan(arms, "ARMS near-plane upper-right quadrant (by bone group):", arms_group)

gun = bpy.data.objects["ASH12_Export"]
slot_of_vertex = {}
for poly in gun.data.polygons:
    for v in poly.vertices:
        slot_of_vertex.setdefault(v, poly.material_index)


def gun_group(i):
    s = slot_of_vertex.get(i, -1)
    return gun.material_slots[s].name if 0 <= s < len(gun.material_slots) else "?"


scan(gun, "GUN near-plane upper-right quadrant (by material):", gun_group)
print("\nASH12_NEARPLANE_COMPLETE")
