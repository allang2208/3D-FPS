"""Two measurements the stills cannot answer: is the magazine visible from the
player's eye, and how deep does the arm mesh sit inside the gun.

The eye comes from the shipped ADS calibration (ADSRearEyeDistance behind the
rear sight, along the sight axis), so "visible" here means visible in the real
first-person framing, not in some chosen review camera.

Run: blender --background --factory-startup --python-exit-code 1 --python probe_reload_visibility.py
"""
import os

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
FRAMES = [float(f) for f in os.environ.get(
    "ASH12_FRAMES", "0,14,21,28,34,42,48,54,62,70,80,96,104,112,120,128,136,150,162").split(",")]
DEPTH = 0.003          # metres a vertex has to be inside before it counts

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


aim = set_action("ASH12_aim", 0)
rear = aim["WPN_RearSight"].translation.copy()
front = aim["WPN_FrontSight"].translation.copy()
fwd = (front - rear).normalized()
EYE = rear - fwd * 0.18
print("ASH12_EYE %s" % (tuple(round(c, 4) for c in EYE),))

# Magazine vertices, taken from the magazine material slots.
mag_slots = {i for i, m in enumerate(gun.data.materials) if m and "Magazine" in m.name}
mag_verts = set()
for poly in gun.data.polygons:
    if poly.material_index in mag_slots:
        mag_verts.update(poly.vertices)
mag_verts = sorted(mag_verts)
print("ASH12_MAG_VERTS %d" % len(mag_verts))

action = bpy.data.actions["ASH12_reload_empty"]
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]

print("\n  frame  mag visible   deepest arm/gun overlap   worst bone")
for frame in FRAMES:
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    gun_eval = gun.evaluated_get(depsgraph)
    gun_mesh = gun_eval.to_mesh()
    gun_map = gun_eval.matrix_world
    gun_tree = BVHTree.FromPolygons([gun_map @ v.co for v in gun_mesh.vertices],
                                    [tuple(p.vertices) for p in gun_mesh.polygons], all_triangles=False)
    gun_points = [gun_map @ v.co for v in gun_mesh.vertices]

    # 1. Is the magazine visible from the eye? A ray that meets a non-magazine
    #    polygon first is blocked by the gun itself.
    seen = blocked = 0
    blocked_by = {}
    for index in mag_verts[::4]:
        point = gun_points[index]
        direction = (point - EYE)
        length = direction.length
        direction = direction / length
        location, normal, poly, distance = gun_tree.ray_cast(EYE, direction, length + 0.001)
        if location is None:
            seen += 1
            continue
        materials = [gun_mesh.materials[i].name if gun_mesh.materials[i] else "?" for i in range(len(gun_mesh.materials))]
        name = materials[gun_mesh.polygons[poly].material_index] if poly is not None and poly < len(gun_mesh.polygons) else "?"
        if "Magazine" in name:
            seen += 1
        else:
            blocked += 1
            blocked_by[name] = blocked_by.get(name, 0) + 1
    percent = 100.0 * seen / max(1, seen + blocked)

    # 2. How deep does the arm mesh sit inside the gun? Nearest-surface normals,
    #    which over-report points far from the mesh (an arm 0.14 m outside the
    #    receiver still gets a nearest face pointing the other way) -- so read it
    #    as a relative number against the accepted frame-0 hold, not as millimetres
    #    of real penetration. Ray parity is no better on this non-manifold mesh.
    def inside_depth(tree, point):
        location, normal, poly, distance = tree.find_nearest(point, 0.12)
        if location is None:
            return 0.0
        return distance if (point - location).dot(normal) < 0.0 else 0.0

    arms_eval = arms.evaluated_get(depsgraph)
    arms_mesh = arms_eval.to_mesh()
    arms_map = arms_eval.matrix_world
    root_inv = rig.pose.bones["WPN_root"].matrix.inverted()
    worst = (0.0, None, "")
    inside = 0
    for vertex in arms_mesh.vertices:
        point = arms_map @ vertex.co
        depth = inside_depth(gun_tree, point)
        if depth > DEPTH:
            inside += 1
            if depth > worst[0]:
                groups = arms.data.vertices[vertex.index].groups
                owner = max(groups, key=lambda g: g.weight).group if groups else -1
                bone = arms.vertex_groups[owner].name if owner >= 0 else "?"
                worst = (depth, root_inv @ point, bone)
    arms_eval.to_mesh_clear()
    gun_eval.to_mesh_clear()
    # How far the curled fingers are from the charging handle: the hand has to
    # wrap it, not sit inside the receiver next to it.
    handle = rig.pose.bones["WPN_ChargingHandle"].matrix.translation.copy()
    mag = rig.pose.bones["WPN_SOCKET_Magazine"].matrix.translation.copy()
    fingers = ("index_02_r", "index_03_r", "middle_02_r", "middle_03_r")
    grip = min((rig.pose.bones[name].matrix.translation - handle).length for name in fingers)
    magazine = min((rig.pose.bones[name].matrix.translation - mag).length for name in fingers)
    where = "n/a"
    if worst[1] is not None:
        local = worst[1]
        where = "recv=(%.2f,%.2f,%.2f)" % (local.x, local.y, local.z)
    top = max(blocked_by.items(), key=lambda kv: kv[1])[0] if blocked_by else "-"
    print("  %5.0f   %5.1f%%        %6.1f mm (%4d verts)  %-14s %-10s handle %5.0f mm  magazine %5.0f mm"
          % (frame, percent, worst[0] * 1000.0, inside, worst[2], where, grip * 1000, magazine * 1000))

print("\nASH12_VISIBILITY_COMPLETE")
