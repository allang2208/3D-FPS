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
CUT_FRACTION = 0.45       # share of the magazine left above the cut


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

# Cut plane through the magazine, keeping the insertion section above it. The
# whole lower body moves as one piece along the magazine axis, so the insertion
# section, its angle and its seat are untouched (same rule as the QBZ-40 build).
heights = sorted((p - centroid).dot(axis_up) for p in points)
cut = heights[int(len(heights) * CUT_FRACTION)]
below = [(object_mesh.matrix_world @ v.co - centroid).dot(axis_up) < cut for v in mesh.vertices]
print("EXMAG_CUT", round(cut, 5), "below", sum(1 for b in below if b), "of", len(below), flush=True)

# Move the body below the cut along the magazine axis. The shift ramps in over a
# short band instead of switching on at the cut: a curved magazine would show a
# hard step there, while a smooth ramp reads as a longer body (the straight
# QBZ-40 magazine could take the hard version).
shift_world = -axis_up * EXTENSION
shift_local = object_mesh.matrix_world.inverted().to_3x3() @ shift_world
BAND = 0.045
for vertex in mesh.vertices:
    height = (object_mesh.matrix_world @ vertex.co - centroid).dot(axis_up)
    weight = max(0.0, min(1.0, (cut - height) / BAND))
    weight = weight * weight * (3.0 - 2.0 * weight)      # smoothstep
    if weight > 0.0:
        vertex.co = vertex.co + shift_local * weight
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
    "cut_fraction": CUT_FRACTION,
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
