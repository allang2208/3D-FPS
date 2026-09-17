"""Sweep the receiver's pose and measure how much of the magazine the player can
actually see from the shipped eye position.

Visibility depends only on where the receiver is, so this poses the gun directly
instead of rebuilding the clips: the answer is a design choice (how far the
receiver tips and rolls while the magazine is worked), and it is cheaper to read
it off a grid than off renders.

Run: blender --background --factory-startup --python-exit-code 1 --python sweep_mag_visibility.py
"""
import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
gun = bpy.data.objects["ASH12_Export"]
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
EYE = rear - (front - rear).normalized() * 0.18

# The hold the clip starts from, and the magazine's own vertices.
base = set_action("ASH12_reload_empty", 0)
root0 = base["WPN_root"].copy()
mag_slots = {i for i, m in enumerate(gun.data.materials) if m and "Magazine" in m.name}
mag_verts = sorted({v for p in gun.data.polygons if p.material_index in mag_slots for v in p.vertices})


def measure(pitch, yaw, roll, mag_drop):
    """Magazine visible fraction for a receiver tipped and rolled this far."""
    rigid = (root0
             @ Matrix.Translation(Vector((0.0, 0.0, -mag_drop)))
             @ Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(roll)).to_matrix().to_4x4()
             @ Quaternion(Vector((0.0, 0.0, 1.0)), math.radians(yaw)).to_matrix().to_4x4()
             @ Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(pitch)).to_matrix().to_4x4())
    depsgraph = bpy.context.evaluated_depsgraph_get()
    view = bpy.data.objects.new("view", gun.data.copy())
    scene.collection.objects.link(view)
    view.modifiers.clear()
    view.matrix_world = Matrix.Identity(4)
    # Deformed gun positions, then the trial pose on top of them.
    evaluated = gun.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    base_matrix = evaluated.matrix_world
    points = [rigid @ (base_matrix @ v.co) for v in mesh.vertices]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    materials = [m.name if m else "?" for m in mesh.materials]
    poly_material = [materials[p.material_index] for p in mesh.polygons]
    tree = BVHTree.FromPolygons(points, polygons, all_triangles=False)
    seen = blocked = 0
    for index in mag_verts[::4]:
        point = points[index]
        direction = point - EYE
        length = direction.length
        location, normal, poly, distance = tree.ray_cast(EYE, direction / length, length + 0.001)
        if location is None or poly is None or "Magazine" in poly_material[poly]:
            seen += 1
        else:
            blocked += 1
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(view, do_unlink=True)
    return 100.0 * seen / max(1, seen + blocked)


print("\n=== magazine visibility from the eye, %% (rows: pitch muzzle-up) ===")
print("  pitch | mag_drop |  roll 0   15   30   45   60   75   90")
for pitch in (0.0, -10.0, -20.0, -30.0):
    for drop in (0.0, 0.06):
        row = []
        for roll in (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0):
            row.append("%5.1f" % measure(pitch, 0.0, roll, drop))
        print("  %5.0f | %7.2f | %s" % (pitch, drop, " ".join(row)))

print("\nASH12_SWEEP_COMPLETE")
