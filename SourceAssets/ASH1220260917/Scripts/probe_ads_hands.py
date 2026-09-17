"""Why the firing hand reads as a blob in ADS.

The ADS camera sits ADSRearEyeDistance behind the rear sight, which is much
closer to the hands than the hip view. This reports, for the aim and idle poses,
how close the arm mesh comes to that eye and how far it sits inside the gun.

Run: blender --background --factory-startup --python-exit-code 1 --python probe_ads_hands.py
"""
import os

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
gun = bpy.data.objects["ASH12_Export"]
arms = bpy.data.objects["SK_Manny_Arms_Export"]
if not rig.animation_data:
    rig.animation_data_create()


def set_action(name, frame):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


EFFECTIVE_EYE = 0.18
for clip in ("ASH12_aim", "ASH12_idle", "ASH12_reload_empty"):
    for frame in (0.0, 0.0 if clip != "ASH12_reload_empty" else 21.0,
                  21.0 if clip == "ASH12_reload_empty" else 0.0):
        pose = set_action(clip, frame)
        rear = pose["WPN_RearSight"].translation.copy()
        front = pose["WPN_FrontSight"].translation.copy()
        eye = rear - (front - rear).normalized() * EFFECTIVE_EYE

        depsgraph = bpy.context.evaluated_depsgraph_get()
        gun_eval = gun.evaluated_get(depsgraph)
        gun_mesh = gun_eval.to_mesh()
        gun_map = gun_eval.matrix_world
        tree = BVHTree.FromPolygons([gun_map @ v.co for v in gun_mesh.vertices],
                                    [tuple(p.vertices) for p in gun_mesh.polygons], all_triangles=False)
        arms_eval = arms.evaluated_get(depsgraph)
        arms_mesh = arms_eval.to_mesh()
        arms_map = arms_eval.matrix_world
        root_inv = pose["WPN_root"].inverted()

        nearest = (1e9, "", None)
        worst = (0.0, "", None)
        inside = 0
        for vertex in arms_mesh.vertices:
            point = arms_map @ vertex.co
            distance = (point - eye).length
            if distance < nearest[0]:
                groups = arms.data.vertices[vertex.index].groups
                owner = max(groups, key=lambda g: g.weight).group if groups else -1
                name = arms.vertex_groups[owner].name if owner >= 0 else "?"
                nearest = (distance, name, root_inv @ point)
            location, normal, poly, gap = tree.find_nearest(point, 0.12)
            if location is not None and (point - location).dot(normal) < 0.0 and gap > 0.003:
                inside += 1
                if gap > worst[0]:
                    groups = arms.data.vertices[vertex.index].groups
                    owner = max(groups, key=lambda g: g.weight).group if groups else -1
                    name = arms.vertex_groups[owner].name if owner >= 0 else "?"
                    worst = (gap, name, root_inv @ point)
        arms_eval.to_mesh_clear()
        gun_eval.to_mesh_clear()
        where = "n/a" if nearest[2] is None else "(%.2f,%.2f,%.2f)" % tuple(nearest[2])
        print("%-22s f=%-5.0f  eye->hand %5.1f mm (%s %s)   inside gun %5.1f mm (%s, %d verts)"
              % (clip, frame, nearest[0] * 1000, nearest[1], where, worst[0] * 1000, worst[1], inside))

print("\nASH12_ADS_HANDS_COMPLETE")
