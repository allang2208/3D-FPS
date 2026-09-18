"""Build the AKM extended magazine out of the AKM's own factory magazine.

Why this route: the earlier AKM asset was the M4 PMAG fitted to the AKM well by
hand, which both missed the well and looked like another rifle's part. The
authoritative AKM source FBX already carries the factory magazine as its own
material section (`M_AKM_Soviet_Magazine`, inside `AKM_Soviet_Native`), so the
extended magazine can be that exact geometry: the insertion section and its
position are untouched, only the body below the cut moves 6 cm further down.
The part therefore lands where the rifle's own magazine sits and keeps the
rifle's own magazine material and UVs.

Run: blender -b -P build_extmag_from_factory.py
"""
import bpy
import bmesh
import json
import math
import numpy as np
import os
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FBXDIR = os.path.join(ROOT, "FBX")
OUT_FBX = os.path.join(FBXDIR, "SM_ExtMag_AKM40_factory.fbx")
OUT_BLEND = os.path.join(ROOT, "ExtMag40_AKM_Editable.blend")
RIFLE_FBX = (r"D:\FPS3D\FPSGAME\SourceAssets\PhantomRearGripIntegration20260913"
             r"\AKM\SK_AKM_MannyNative.fbx")
MAG_OBJECT = "AKM_FactoryMagazine_Preview"
MAG_SLOT = "M_AKM_Soviet_Magazine"
EXTENSION = 0.06          # 6 cm, the accepted +10 round extension
# Where the extension band sits along the magazine. It has to stay clear of the
# reload animation's left-hand grip: the accepted reload closes the hand on the
# upper body, so the 6 cm that gets stretched goes low, just above the floor
# plate, and the surface the fingers wrap stays factory geometry.
BAND_FRACTION = 0.12


def import_fbx(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def bounds(points):
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


bpy.ops.wm.read_factory_settings(use_empty=True)
objs = import_fbx(RIFLE_FBX)
rifle = next(o for o in objs if o.type == "MESH" and o.name == MAG_OBJECT)
arm = next(o for o in objs if o.type == "ARMATURE")
arm.data.pose_position = "REST"
bpy.context.view_layer.update()
print("EXMAG_SOURCES", [(o.name, o.type) for o in objs], flush=True)

slot_index = next(i for i, m in enumerate(rifle.data.materials) if m and m.name == MAG_SLOT)
print("EXMAG_SLOT", MAG_SLOT, "index", slot_index, flush=True)

# Duplicate the factory magazine object, so nothing else in the scene can be
# dragged along by the extension.
mesh = rifle.data.copy()
mesh.name = "AKM_ExtMagazine"
object_mesh = bpy.data.objects.new("AKM_ExtMagazine", mesh)
bpy.context.scene.collection.objects.link(object_mesh)
object_mesh.matrix_world = rifle.matrix_world.copy()
for modifier in list(object_mesh.modifiers):
    object_mesh.modifiers.remove(modifier)

bpy.context.view_layer.objects.active = object_mesh
bpy.ops.object.select_all(action='DESELECT')
object_mesh.select_set(True)
counts = {}
for poly in mesh.polygons:
    counts[poly.material_index] = counts.get(poly.material_index, 0) + 1
print("EXMAG_FACES_PER_SLOT", counts, flush=True)

bm = bmesh.new()
bm.from_mesh(mesh)
for face in bm.faces:
    face.material_index = 0
bm.to_mesh(mesh)
bm.free()
mesh.update()
print("EXMAG_EXTRACTED verts", len(mesh.vertices), "polys", len(mesh.polygons), flush=True)
# Keep only the magazine slot (and its material), so the UE asset has one slot.
kept = mesh.materials[slot_index]
mesh.materials.clear()
mesh.materials.append(kept)
for poly in mesh.polygons:
    poly.material_index = 0

points = [object_mesh.matrix_world @ v.co for v in mesh.vertices]
lo, hi = bounds(points)
print("EXMAG_FACTORY verts", len(mesh.vertices), "polys", len(mesh.polygons),
      "lo", tuple(round(v, 4) for v in lo), "hi", tuple(round(v, 4) for v in hi),
      "dims_cm", tuple(round((hi - lo)[i] * 100, 2) for i in range(3)), flush=True)

# Axis: the magazine runs from the well (the socket bone) down to its floor
# plate, so the up direction is the one that points at the socket.
socket = arm.matrix_world @ arm.data.bones["WPN_SOCKET_Magazine"].head_local if \
    hasattr(arm.data.bones["WPN_SOCKET_Magazine"], "head_local") else \
    arm.matrix_world @ Vector(arm.data.bones["WPN_SOCKET_Magazine"].head_local)
centroid = sum(points, Vector()) / len(points)
axis_up = (socket - centroid)
axis_up.normalize()
print("EXMAG_AXIS", tuple(round(v, 5) for v in axis_up),
      "socket", tuple(round(v, 5) for v in socket), flush=True)

# Lengthen by moving each cross-section down **its own local direction** and
# ramping the amount in over one band, so the body follows the magazine's
# curvature instead of being dragged along one straight axis. The first pass
# used a single axis: the plate then sat off the curve and the bottom read as a
# pointed wedge, and inserting a copied band (with welding) left open edges at
# the seam. Ribs stretch inside the 6 cm band, exactly the accepted QBZ-40
# behaviour, and the floor plate, taper and throat keep their factory shape.
def slice_centroids(points, up, bins=24):
    along = [(p - centroid).dot(up) for p in points]
    low, high = min(along), max(along)
    rows = []
    for index in range(bins):
        limit_a = low + (high - low) * index / bins
        limit_b = low + (high - low) * (index + 1) / bins
        group = [p for p, value in zip(points, along) if limit_a <= value < limit_b]
        if len(group) < 8:
            continue
        rows.append((sum(along_value for along_value in
                         [(p - centroid).dot(up) for p in group]) / len(group),
                     sum(group, Vector()) / len(group)))
    return rows


slices = slice_centroids(points, axis_up)
print("EXMAG_SLICES", [(round(c.y, 4), round(c.z, 4)) for _, c in slices], flush=True)
# Magazine axis: the direction through the slice centroids (long baseline, so
# the socket-based guess is not used for the move itself).
axis_origin = sum((c for _, c in slices), Vector()) / len(slices)
axis_dir = Vector((0.0, 0.0, 0.0))
for _, point in slices:
    delta = point - axis_origin
    axis_dir += delta * (delta.length ** 2)
if axis_dir.length < 1e-6:
    axis_dir = axis_up
axis_dir.normalize()
if axis_dir.dot(axis_up) < 0:
    axis_dir = -axis_dir
print("EXMAG_AXIS_DIR", tuple(round(v, 5) for v in axis_dir), flush=True)

along = [(object_mesh.matrix_world @ v.co - axis_origin).dot(axis_dir) for v in mesh.vertices]
# Bands are placed by position along the magazine, not by vertex percentile: the
# plate and the bottom ribs hold most of the vertices, so a percentile lands at
# the very bottom and the copy ends up hanging below the floor plate.
along_low, along_high = min(along), max(along)
band_bottom = along_low + (along_high - along_low) * BAND_FRACTION
band_top = band_bottom + EXTENSION

# The magazine is not perfectly straight: the band's own axis is a few degrees
# off the overall one, and inserting the copy along the overall axis leaves the
# copy offset sideways (a visible step at the seam). Take the band's own axis
# from the slice centroids inside it, then cut and move along that.
inside = [(value, centre) for value, centre in slices
          if band_bottom - 0.02 <= value <= band_top + 0.02]
local_axis = axis_dir
if len(inside) >= 4:
    third = max(1, len(inside) // 3)
    top_centre = sum((c for _, c in inside[-third:]), Vector()) / third
    bottom_centre = sum((c for _, c in inside[:third]), Vector()) / third
    if (top_centre - bottom_centre).length > 1e-5:
        local_axis = (top_centre - bottom_centre).normalized()
        if local_axis.dot(axis_dir) < 0:
            local_axis = -local_axis
print("EXMAG_LOCAL_AXIS", tuple(round(v, 5) for v in local_axis),
      "tilt_deg", round(math.degrees(math.acos(max(-1.0, min(1.0, local_axis.dot(axis_dir))))), 2),
      flush=True)

along = [(object_mesh.matrix_world @ v.co - axis_origin).dot(local_axis) for v in mesh.vertices]
along_low, along_high = min(along), max(along)
band_bottom = along_low + (along_high - along_low) * BAND_FRACTION
band_top = band_bottom + EXTENSION
print("EXMAG_BAND", round(band_top, 4), round(band_bottom, 4), flush=True)

# Slice centroids wobble with the ribs, so the local direction comes from a
# quadratic fit through them: a smooth centre line whose derivative is the
# magazine's own tangent at that height.
slice_values = np.array([value for value, _ in slices], dtype=float)
slice_points = np.array([[centre.x, centre.y, centre.z] for _, centre in slices], dtype=float)
polynomials = [np.polyfit(slice_values, slice_points[:, axis], 2) for axis in range(3)]


def local_direction(value):
    derivative = np.array([np.polyval(np.polyder(poly), value) for poly in polynomials], dtype=float)
    direction = Vector((float(derivative[0]), float(derivative[1]), float(derivative[2])))
    if direction.length < 1e-6:
        return local_axis
    direction.normalize()
    if direction.dot(local_axis) < 0:
        direction = -direction
    return direction


probe_values = [slice_values[0] + (slice_values[-1] - slice_values[0]) * step / 6.0 for step in range(7)]
print("EXMAG_TANGENTS",
      [(round(value, 3),
        round(math.degrees(math.acos(max(-1.0, min(1.0, local_direction(value).dot(local_axis))))), 2))
       for value in probe_values], flush=True)


world_to_local = object_mesh.matrix_world.inverted()
for vertex in mesh.vertices:
    point = object_mesh.matrix_world @ vertex.co
    value = (point - axis_origin).dot(local_axis)
    ramp = (band_top - value) / EXTENSION
    if ramp <= 0.0:
        continue
    ramp = min(1.0, ramp)
    ramp = ramp * ramp * (3.0 - 2.0 * ramp)          # smoothstep
    vertex.co = world_to_local @ (point - local_direction(value) * (EXTENSION * ramp))
mesh.update()

new_points = [object_mesh.matrix_world @ v.co for v in mesh.vertices]
nlo, nhi = bounds(new_points)
print("EXMAG_EXTENDED verts", len(mesh.vertices), "polys", len(mesh.polygons),
      "lo", tuple(round(v, 4) for v in nlo), "hi", tuple(round(v, 4) for v in nhi),
      "dims_cm", tuple(round((nhi - nlo)[i] * 100, 2) for i in range(3)),
      "length_cm", round((nhi - nlo).length * 100, 2), flush=True)

# The part keeps the factory UV0 and normals; UV1 (the old coating bake) is gone.
print("EXMAG_UV", [layer.name for layer in mesh.uv_layers],
      "mats", [m.name if m else None for m in mesh.materials], flush=True)

# Export in the same convention as the other extended-magazine meshes.
for obj in list(bpy.context.scene.objects):
    if obj is not object_mesh:
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
object_mesh.select_set(True)
bpy.context.view_layer.objects.active = object_mesh
bpy.ops.export_scene.fbx(filepath=OUT_FBX, use_selection=True, object_types={'MESH'},
                         axis_forward='-Y', axis_up='Z', bake_anim=False,
                         mesh_smooth_type='FACE', use_tspace=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

report = {
    "source": RIFLE_FBX,
    "source_object": MAG_OBJECT,
    "source_slot": MAG_SLOT,
    "extension_cm": EXTENSION * 100,
    "band_fraction": BAND_FRACTION,
    "axis_up": [round(v, 6) for v in axis_up],
    "factory_bounds": [list(round(v, 5) for v in lo), list(round(v, 5) for v in hi)],
    "extended_bounds": [list(round(v, 5) for v in nlo), list(round(v, 5) for v in nhi)],
    "factory_dims_cm": [round((hi - lo)[i] * 100, 2) for i in range(3)],
    "extended_dims_cm": [round((nhi - nlo)[i] * 100, 2) for i in range(3)],
    "vertices": len(mesh.vertices),
    "polygons": len(mesh.polygons),
    "uv_layers": [layer.name for layer in mesh.uv_layers],
    "materials": [m.name if m else None for m in mesh.materials],
    "fbx": OUT_FBX,
    "editable": OUT_BLEND,
}
with open(os.path.join(ROOT, "Reference", "akm40_factory_build.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1, ensure_ascii=False)
print("EXTMAG_AKM_BUILD " + json.dumps(report), flush=True)
