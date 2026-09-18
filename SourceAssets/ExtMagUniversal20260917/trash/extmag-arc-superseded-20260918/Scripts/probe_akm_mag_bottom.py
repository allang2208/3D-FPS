"""Probe why the extended AKM magazine reads pointed at its bottom (read-only).

Checks the extracted factory magazine for open boundaries (a missing floor
plate leaves a knife-edge shell) and looks for that plate in the rifle mesh.
"""
import bpy
import bmesh
from mathutils import Vector

RIFLE_FBX = (r"D:\FPS3D\FPSGAME\SourceAssets\PhantomRearGripIntegration20260913"
             r"\AKM\SK_AKM_MannyNative.fbx")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=RIFLE_FBX)
rifle = bpy.data.objects["AKM_Soviet_Native"]
mag = bpy.data.objects["AKM_FactoryMagazine_Preview"]

for ob, label in ((mag, "mag"), (rifle, "rifle")):
    print("PROBE", label, "verts", len(ob.data.vertices), "polys", len(ob.data.polygons),
          "mats", [(i, m.name if m else None) for i, m in enumerate(ob.data.materials)], flush=True)

# Open edges of the extracted magazine (boundaries the factory mesh closes with
# other parts, e.g. the floor plate).
bm = bmesh.new()
bm.from_mesh(mag.data)
boundary = [edge for edge in bm.edges if len(edge.link_faces) == 1]
print("PROBE mag_boundary_edges", len(boundary), flush=True)
if boundary:
    verts = {v for edge in boundary for v in edge.verts}
    co = [mag.matrix_world @ v.co for v in verts]
    lo = Vector((min(p.x for p in co), min(p.y for p in co), min(p.z for p in co)))
    hi = Vector((max(p.x for p in co), max(p.y for p in co), max(p.z for p in co)))
    print("PROBE mag_boundary_bounds", tuple(round(v, 4) for v in lo), tuple(round(v, 4) for v in hi),
          "loops:", flush=True)
    # Group boundary verts into connected loops and report each one's size and place.
    remaining = set(verts)
    loops = []
    while remaining:
        seed = remaining.pop()
        stack, group = [seed], [seed]
        while stack:
            current = stack.pop()
            for edge in current.link_edges:
                if len(edge.link_faces) != 1:
                    continue
                other = edge.other_vert(current)
                if other in remaining:
                    remaining.discard(other)
                    stack.append(other)
                    group.append(other)
        loops.append(group)
    for index, group in enumerate(loops):
        pts = [mag.matrix_world @ v.co for v in group]
        center = sum(pts, Vector()) / len(pts)
        print("PROBE loop", index, "verts", len(group),
              "center", tuple(round(v, 4) for v in center), flush=True)
bm.free()

# Anything else sitting at the magazine's floor-plate end?
mag_pts = [mag.matrix_world @ v.co for v in mag.data.vertices]
lowest = min(p.z for p in mag_pts)
slab = [p for p in mag_pts if p.z < lowest + 0.03]
print("PROBE mag_lowest", round(lowest, 4), "verts_in_bottom_3cm", len(slab), flush=True)
for index, mat in enumerate(rifle.data.materials):
    faces = [p for p in rifle.data.polygons if p.material_index == index]
    near = [p for p in faces
            if lowest - 0.02 < (rifle.matrix_world @ p.center).z < lowest + 0.05
            and 0.10 < (rifle.matrix_world @ p.center).y < 0.40]
    if near:
        pts = [rifle.matrix_world @ p.center for p in near]
        print("PROBE rifle_slot", mat.name if mat else index, "faces_near_mag_bottom", len(near),
              "bounds", tuple(round(min(p[i] for p in pts), 4) for i in range(3)),
              tuple(round(max(p[i] for p in pts), 4) for i in range(3)), flush=True)
print("PROBE_DONE", flush=True)
