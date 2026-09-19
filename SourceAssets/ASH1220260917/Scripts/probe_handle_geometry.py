"""Measure the ASH-12 charging-handle geometry, not just its bone.

The handle mesh is bound to ``WPN_ChargingHandle`` with an offset, so the
bone head is not the part the hand has to touch.  This probe prints the real
handle bounding box, the handle/bolt/boot-catch bone travel, and the shortest
distance from the firing-hand knuckles to the handle geometry.

Run: blender --background --factory-startup --python-exit-code 1 --python probe_handle_geometry.py
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

handle_group = gun.vertex_groups.get("WPN_ChargingHandle")
if handle_group is None:
    raise RuntimeError("WPN_ChargingHandle vertex group missing")
handle_verts = []
for vertex in gun.data.vertices:
    if any(member.group == handle_group.index and member.weight > 0.5 for member in vertex.groups):
        handle_verts.append(vertex.index)
print("ASH12_HANDLE_VERTS %d" % len(handle_verts))


def set_action(name, frame):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()


def sample(action_name, frames):
    print("\n=== %s ===" % action_name)
    for frame in frames:
        set_action(action_name, frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        gun_eval = gun.evaluated_get(depsgraph)
        mesh = gun_eval.to_mesh()
        world = gun_eval.matrix_world
        points = [world @ mesh.vertices[index].co for index in handle_verts]
        lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
        hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
        center = (lo + hi) * 0.5
        handle = rig.pose.bones["WPN_ChargingHandle"].matrix.translation
        bolt = rig.pose.bones["WPN_bolt"].matrix.translation
        catch = rig.pose.bones["WPN_BoltCatch"].matrix.translation
        fingers = [rig.pose.bones[name].matrix.translation
                   for name in ("index_01_r", "index_02_r", "index_03_r",
                                "middle_01_r", "middle_02_r", "middle_03_r")]
        nearest = min((finger - point).length for finger in fingers for point in points)
        print("f=%6.1f center=(%.4f,%.4f,%.4f) bbox=(%.4f,%.4f,%.4f)-(%.4f,%.4f,%.4f) "
              "bone=(%.4f,%.4f,%.4f) bolt=(%.4f,%.4f,%.4f) catch=(%.4f,%.4f,%.4f) finger_min=%.4f"
              % (frame, center.x, center.y, center.z, lo.x, lo.y, lo.z, hi.x, hi.y, hi.z,
                 handle.x, handle.y, handle.z, bolt.x, bolt.y, bolt.z, catch.x, catch.y, catch.z,
                 nearest))
        gun_eval.to_mesh_clear()


sample("ASH12_reload_empty", [0.0, 100.0, 108.0, 110.0, 118.0, 120.0, 126.0, 130.0, 133.0, 138.0, 162.0])
sample("ASH12_equip_charge", [0.0, 8.0, 16.0, 24.0, 30.0, 38.0])

# Rest geometry: the reference video grips the handle from above, palm down.
# Measure the handle's receiver-local top face and the accepted grip's palm
# normal so the roll for the overhand grip is derived, not guessed.
set_action("ASH12_idle", 0.0)
depsgraph = bpy.context.evaluated_depsgraph_get()
gun_eval = gun.evaluated_get(depsgraph)
mesh = gun_eval.to_mesh()
world = gun_eval.matrix_world
root_local = rig.pose.bones["WPN_root"].matrix.inverted()
points_local = [root_local @ (world @ mesh.vertices[index].co) for index in handle_verts]
lo_local = Vector((min(p.x for p in points_local), min(p.y for p in points_local), min(p.z for p in points_local)))
hi_local = Vector((max(p.x for p in points_local), max(p.y for p in points_local), max(p.z for p in points_local)))
hand = root_local @ rig.pose.bones["hand_r"].matrix.translation
index = root_local @ rig.pose.bones["index_01_r"].matrix.translation
thumb = root_local @ rig.pose.bones["thumb_01_r"].matrix.translation
finger_dir = (index - hand).normalized()
side_dir = (thumb - index).normalized()
palm_normal = finger_dir.cross(side_dir).normalized()
print("ASH12_HANDLE_LOCAL_BBOX lo=(%.4f,%.4f,%.4f) hi=(%.4f,%.4f,%.4f)"
      % (lo_local.x, lo_local.y, lo_local.z, hi_local.x, hi_local.y, hi_local.z))
print("ASH12_HAND_AXES hand=(%.4f,%.4f,%.4f) finger=(%.4f,%.4f,%.4f) side=(%.4f,%.4f,%.4f) palm=(%.4f,%.4f,%.4f)"
      % (hand.x, hand.y, hand.z, finger_dir.x, finger_dir.y, finger_dir.z,
         side_dir.x, side_dir.y, side_dir.z, palm_normal.x, palm_normal.y, palm_normal.z))
hand_rot = (root_local.to_3x3() @ rig.pose.bones["hand_r"].matrix.to_3x3())
for axis_name, axis_vector in (("X", Vector((1.0, 0.0, 0.0))),
                               ("Y", Vector((0.0, 1.0, 0.0))),
                               ("Z", Vector((0.0, 0.0, 1.0)))):
    axis = (hand_rot @ axis_vector).normalized()
print("ASH12_HAND_AXIS_%s (%.4f,%.4f,%.4f) dot_finger=%.3f dot_side=%.3f dot_palm=%.3f"
          % (axis_name, axis.x, axis.y, axis.z,
             axis.dot(finger_dir), axis.dot(side_dir), axis.dot(palm_normal)))
gun_eval.to_mesh_clear()


def hand_axes(action_name, frame, label):
    set_action(action_name, frame)
    root_inv = rig.pose.bones["WPN_root"].matrix.inverted()
    hand = root_inv @ rig.pose.bones["hand_r"].matrix.translation
    index = root_inv @ rig.pose.bones["index_01_r"].matrix.translation
    thumb = root_inv @ rig.pose.bones["thumb_01_r"].matrix.translation
    finger = (index - hand).normalized()
    side = (thumb - index).normalized()
    palm = finger.cross(side).normalized()
    print("ASH12_HAND_AXES_%s f=%.0f hand=(%.4f,%.4f,%.4f) finger=(%.4f,%.4f,%.4f) side=(%.4f,%.4f,%.4f) palm=(%.4f,%.4f,%.4f)"
          % (label, frame, hand.x, hand.y, hand.z, finger.x, finger.y, finger.z,
             side.x, side.y, side.z, palm.x, palm.y, palm.z))


hand_axes("ASH12_reload_empty", 0.0, "REST")
hand_axes("ASH12_reload_empty", 120.0, "PULL")
print("\nASH12_HANDLE_GEOMETRY_COMPLETE")
