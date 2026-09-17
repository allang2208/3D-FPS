"""Second pass: what the magazine parts actually are, and where the handguard is.

Run: blender --background --factory-startup --python-exit-code 1 --python inspect_magazine.py
"""
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
rig = bpy.data.objects["SK_M4_Infima"]
gun = bpy.data.objects["ASH12_Export"]
root_head = rig.data.bones["WPN_root"].matrix_local.translation.copy()

# recv: the frame the clips are authored in (bone-local of WPN_root at rest).
def recv(world):
    local = rig.data.bones["WPN_root"].matrix_local.inverted() @ Vector(world)
    return local


def bounds(points):
    lo = Vector((min(p[i] for p in points) for i in range(3)))
    hi = Vector((max(p[i] for p in points) for i in range(3)))
    return lo, hi


me = gun.data
by_material = {}
for poly in me.polygons:
    name = me.materials[poly.material_index].name
    bucket = by_material.setdefault(name, set())
    for v in poly.vertices:
        bucket.add(v)

print("\n=== PER MATERIAL (armature space -> receiver frame) ===")
for name in sorted(by_material):
    pts = [me.vertices[i].co for i in by_material[name]]
    lo, hi = bounds(pts)
    rlo, rhi = recv(lo), recv(hi)
    # receiver-frame extents sorted so min/max are meaningful despite the axis flip
    rx = sorted((rlo.x, rhi.x))
    ry = sorted((rlo.y, rhi.y))
    rz = sorted((rlo.z, rhi.z))
    print("  %-22s verts=%6d  recv X[%.3f %.3f] Y[%.3f %.3f] Z[%.3f %.3f]"
          % (name, len(pts), rx[0], rx[1], ry[0], ry[1], rz[0], rz[1]))

print("\n=== MAGAZINE ISLANDS ===")
mag_slots = {i for i, m in enumerate(me.materials) if m and ("Magazine" in m.name)}
verts = set()
for poly in me.polygons:
    if poly.material_index in mag_slots:
        verts.update(poly.vertices)
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
seen = set()
islands = []
for idx in sorted(verts):
    if idx in seen:
        continue
    stack = [bm.verts[idx]]
    seen.add(idx)
    members = []
    while stack:
        v = stack.pop()
        members.append(v.index)
        for e in v.link_edges:
            other = e.other_vert(v)
            if other.index in verts and other.index not in seen:
                seen.add(other.index)
                stack.append(other)
    islands.append(members)
bm.free()
print("  islands:", len(islands))
for members in sorted(islands, key=len, reverse=True)[:8]:
    pts = [me.vertices[i].co for i in members]
    lo, hi = bounds(pts)
    rlo, rhi = recv(lo), recv(hi)
    rx = sorted((rlo.x, rhi.x))
    ry = sorted((rlo.y, rhi.y))
    rz = sorted((rlo.z, rhi.z))
    print("    verts=%5d  recv X[%.3f %.3f] Y[%.3f %.3f] Z[%.3f %.3f]"
          % (len(members), rx[0], rx[1], ry[0], ry[1], rz[0], rz[1]))

print("\n=== LEFT HAND AT FRAME 0 OF THE EMPTY RELOAD ===")
scene = bpy.context.scene
action = bpy.data.actions["M4_HK416_reload_empty"]
if not rig.animation_data:
    rig.animation_data_create()
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
inv = pose["WPN_root"].inverted()
for name in ("hand_l", "index_01_l", "thumb_01_l", "middle_01_l", "pinky_01_l"):
    if name in pose:
        r = inv @ pose[name].translation
        print("  %-14s recv=(%.4f, %.4f, %.4f)" % (name, r.x, r.y, r.z))

# Which receiver material sits under the support hand?
point = pose["hand_l"].translation.copy()
inverse = gun.matrix_world.inverted()
local = inverse @ point
# nearest kept polygon
best = None
for poly in me.polygons:
    c = poly.center
    d = (c - local).length
    if best is None or d < best[0]:
        best = (d, me.materials[poly.material_index].name, poly.center.copy())
print("  nearest surface to hand_l: %-20s dist=%.4f m  recv=%s"
      % (best[1], best[0], tuple(round(c, 3) for c in recv(best[2]))))

print("\nASH12_MAGAZINE_INSPECT_COMPLETE")
