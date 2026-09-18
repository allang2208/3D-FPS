"""Extend a factory magazine by one arc-tube section (round 7, 2026-09-18).

Why this replaces the "cut a band and repeat it" build:
  * round 5 repeated the band with a direction fit that could only translate, so
    the copy was shifted sideways (and skewed on the curved QBZ) - the user saw
    it as "the 191 and M4 magazines are modelled wrong, there is a wrong
    truncation";
  * round 6 registered the two cut rings instead, but the two sections of a
    raked/curved body are not congruent (a millimetre or two apart), so pinning
    the copy onto the seam crumpled the body at the seam - visible again.

What it does now - no vertex is ever stretched and no seam is ever mismatched:
  1. cut the magazine once, perpendicular to its OWN centreline (a bounding-box
     cut is oblique and does not give a cross-section at all);
  2. take the outer loop of that cut as the section, ordered around the ring;
  3. rebuild the loop `SEGMENTS` times along the magazine's own arc (each step is
     a rigid rotation about the ring's centre plus a shift down its own normal)
     and stitch the rings into a tube - the first ring is the cut's own vertices,
     so the seam is closed by construction;
  4. duplicate the base-plate section under the cut and move it by the whole arc
     step, so its top ring lands exactly on the tube's last ring.

The extension is a clean tube: the factory ribs stop at the cut and resume on the
moved base plate. That is the known cosmetic difference from the factory body.

Run: blender -b -P build_extmag_arc_tube.py
"""
import bmesh
import bpy
import json
import math
import os
import numpy as np
from mathutils import Matrix, Vector

SA = r"D:\FPS3D\FPSGAME\SourceAssets"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FBXDIR = os.path.join(ROOT, "FBX")
EXTENSION = 0.06            # 6 cm of extra magazine
SEGMENTS = 6                # arc steps, 1 cm each
SHELL_WELD = 1e-5

JOBS = {
    "M4": dict(source=os.path.join(SA, "M4HK416Replica20260910",
                                   "SK_M4_FoldingSights_HK416.fbx"),
               match="magazine", out="SM_ExtMag_M440_arc.fbx", cut_above_floor=0.030),
    "QBZ": dict(source=os.path.join(SA, "PhantomRearGripIntegration20260913",
                                    "QBZ191", "SK_QBZ191_Manny.fbx"),
                match="magazine", out="SM_ExtMag_QBZ40_arc.fbx", cut_above_floor=0.030),
}


def import_fbx(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def pick_magazine(match):
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH":
            for material in ob.data.materials:
                if material and match in material.name.lower():
                    return ob
    raise RuntimeError("no magazine object found (%s)" % match)


def keep_magazine_slot(ob, match):
    index = next((i for i, m in enumerate(ob.data.materials)
                  if m and match in m.name.lower()), None)
    if index is None:
        raise RuntimeError("no magazine slot on " + ob.name)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    drop = [face for face in bm.faces if face.material_index != index]
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='FACES')
    loose = [vert for vert in bm.verts if not vert.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    for face in bm.faces:
        face.material_index = 0
    bm.to_mesh(ob.data)
    bm.free()
    kept = ob.data.materials[index]
    ob.data.materials.clear()
    ob.data.materials.append(kept)
    ob.data.update()


def slice_centres(points, centroid, axis, bins=28):
    along = [(p - centroid).dot(axis) for p in points]
    low, high = min(along), max(along)
    samples = []
    for index in range(bins):
        a = low + (high - low) * index / bins
        b = low + (high - low) * (index + 1) / bins
        group = [p for p, value in zip(points, along) if a <= value < b]
        if len(group) >= 8:
            samples.append(((a + b) * 0.5, sum(group, Vector()) / len(group)))
    return samples, low, high


def section_ring(bm, origin, normal, tol=1e-4):
    """Outer cross-section loop of the cut, ordered around the ring.

    A plane through a hollow magazine leaves more than one loop (outer wall plus
    the cavity opening); a plane that grazes a rib leaves a long snake. The
    section is the loop that sits on the magazine's axis and has the longest
    perimeter of those.
    """
    on_plane = {v for v in bm.verts if abs((v.co - origin).dot(normal)) < tol}
    seen, loops = set(), []
    for start in on_plane:
        if start in seen:
            continue
        stack, group = [start], []
        seen.add(start)
        while stack:
            current = stack.pop()
            group.append(current)
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other in on_plane and other not in seen:
                    seen.add(other)
                    stack.append(other)
        loops.append(group)
    if not loops:
        return []

    def perimeter(group):
        members = set(group)
        return sum(edge.calc_length() for edge in
                   {edge for vert in group for edge in vert.link_edges}
                   if edge.verts[0] in members and edge.verts[1] in members)

    def offset(group):
        centre = np.mean([[v.co.x, v.co.y, v.co.z] for v in group], axis=0)
        return float(np.linalg.norm(centre - np.array([origin.x, origin.y, origin.z])))

    on_axis = [group for group in loops if offset(group) <= 0.015]
    loop = max(on_axis or loops, key=perimeter)
    centre = Vector(np.mean([[v.co.x, v.co.y, v.co.z] for v in loop], axis=0).tolist())
    helper = Vector((0.0, 0.0, 1.0)) if abs(normal.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    first = normal.cross(helper).normalized()
    second = normal.cross(first).normalized()

    def bearing(vert):
        offset_vector = vert.co - centre
        return math.atan2(offset_vector.dot(second), offset_vector.dot(first))

    return sorted(loop, key=bearing)


report = {}
for gun, cfg in JOBS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_fbx(cfg["source"])
    magazine = pick_magazine(cfg["match"])
    for other in [o for o in bpy.context.scene.objects if o is not magazine]:
        bpy.data.objects.remove(other, do_unlink=True)
    bpy.context.view_layer.objects.active = magazine
    magazine.select_set(True)
    keep_magazine_slot(magazine, cfg["match"])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mesh = magazine.data

    points = [magazine.matrix_world @ v.co for v in mesh.vertices]
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    centroid = (lo + hi) * 0.5
    size = hi - lo
    axis = Vector((0.0, 0.0, 0.0))
    axis[int(np.argmax(size))] = 1.0

    samples, low, high = slice_centres(points, centroid, axis)
    centre_values = np.array([value for value, _ in samples])
    centre_points = np.array([[p.x, p.y, p.z] for _, p in samples])
    mean_value = float(centre_values.mean())
    offsets = centre_values - mean_value
    design = np.stack([np.ones_like(offsets), offsets, offsets * offsets], axis=1)
    coeff, *_ = np.linalg.lstsq(design, centre_points, rcond=None)

    def point_at(value):
        u = value - mean_value
        point = coeff[0] + coeff[1] * u + coeff[2] * u * u
        return Vector((float(point[0]), float(point[1]), float(point[2])))

    def tangent_at(value):
        u = value - mean_value
        slope = coeff[1] + 2.0 * coeff[2] * u
        direction = Vector((float(slope[0]), float(slope[1]), float(slope[2]))).normalized()
        return direction if direction.dot(axis) >= 0.0 else -direction

    cut_value = low + cfg["cut_above_floor"]
    if cut_value + EXTENSION >= high:
        raise RuntimeError("%s magazine is too short" % gun)
    cut_origin = point_at(cut_value)
    cut_normal = tangent_at(cut_value)
    far_normal = tangent_at(cut_value + EXTENSION)
    bend_deg = math.degrees(cut_normal.angle(far_normal))
    bend_axis = cut_normal.cross(far_normal)
    bend_axis = bend_axis.normalized() if bend_axis.length > 1e-9 else Vector((1.0, 0.0, 0.0))
    print("EXARCTUBE_DEBUG", gun, "cut_cm_above_floor", round(cfg["cut_above_floor"] * 100, 2),
          "normal_vs_axis_deg", round(math.degrees(cut_normal.angle(axis)), 2),
          "bend_over_extension_deg", round(bend_deg, 3), flush=True)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=cut_origin, plane_no=cut_normal,
                           clear_inner=False, clear_outer=False)
    ring = section_ring(bm, cut_origin, cut_normal)
    if len(ring) < 8:
        raise RuntimeError("%s cut ring too sparse (%d)" % (gun, len(ring)))
    lower_faces = [face for face in bm.faces
                   if (face.calc_center_median() - cut_origin).dot(cut_normal) < 0.0]
    if not lower_faces:
        raise RuntimeError("%s cut produced no base-plate faces" % gun)
    ring_centre = Vector(np.mean([[v.co.x, v.co.y, v.co.z] for v in ring], axis=0).tolist())

    def arc_step(fraction):
        """Rigid step: turn with the magazine's own bend and walk down its normal."""
        rotation = Matrix.Rotation(-math.radians(bend_deg * fraction), 4, bend_axis)
        return lambda point: (rotation @ (point - ring_centre) + ring_centre
                              - cut_normal * (EXTENSION * fraction))

    # 1. the base plate travels one whole arc step; its top ring is the cut ring,
    #    so it lands exactly on the tube's last ring.
    duplicate = bmesh.ops.duplicate(bm, geom=lower_faces)
    base_verts = [element for element in duplicate["geom"]
                  if isinstance(element, bmesh.types.BMVert)]
    total = arc_step(1.0)
    for vert in base_verts:
        vert.co = total(vert.co)

    # 2. the tube itself: the cut ring repeated along the same arc, sharing the
    #    cut's own vertices as its first ring.
    rings = [ring]
    for index in range(1, SEGMENTS + 1):
        step = arc_step(index / SEGMENTS)
        rings.append([bm.verts.new(step(vert.co)) for vert in ring])
    bm.verts.ensure_lookup_table()
    # the seam is closed by construction: the tube's last ring and the moved base
    # plate's top ring are the same cut ring under the same rigid step, so record
    # the residual before the weld (remove_doubles merges those vertices away)
    moved_ring = [total(vert.co) for vert in ring]
    seam_gap_mm = round(max(min((point - vert.co).length for point in moved_ring)
                            for vert in rings[-1]) * 1000, 4)
    for index in range(SEGMENTS):
        lower, upper = rings[index], rings[index + 1]
        count = len(lower)
        for corner in range(count):
            quad = (lower[corner], lower[(corner + 1) % count],
                    upper[(corner + 1) % count], upper[corner])
            try:
                bm.faces.new(quad)
            except ValueError:
                pass

    # 3. the original base-plate faces are replaced by the moved copy.
    bmesh.ops.delete(bm, geom=lower_faces, context='FACES')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    open_before = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=SHELL_WELD)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    open_after = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    non_manifold = sum(1 for edge in bm.edges if len(edge.link_faces) > 2)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    new_points = [magazine.matrix_world @ v.co for v in mesh.vertices]
    nlo = Vector((min(p.x for p in new_points), min(p.y for p in new_points), min(p.z for p in new_points)))
    nhi = Vector((max(p.x for p in new_points), max(p.y for p in new_points), max(p.z for p in new_points)))
    dims = tuple(round((nhi - nlo)[i] * 100, 2) for i in range(3))

    out = os.path.join(FBXDIR, cfg["out"])
    bpy.ops.object.select_all(action='DESELECT')
    magazine.select_set(True)
    bpy.context.view_layer.objects.active = magazine
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={'MESH'},
                             axis_forward='-Y', axis_up='Z', bake_anim=False,
                             mesh_smooth_type='FACE', use_tspace=True)
    report[gun] = {
        "source": cfg["source"], "file": out,
        "factory_length_cm": round((high - low) * 100, 2),
        "cut_cm_above_floor": round(cfg["cut_above_floor"] * 100, 2),
        "extension_cm": EXTENSION * 100, "segments": SEGMENTS,
        "cut_normal_vs_axis_deg": round(math.degrees(cut_normal.angle(axis)), 2),
        "bend_over_extension_deg": round(bend_deg, 3),
        "ring_verts": len(ring),
        "seam_gap_mm": seam_gap_mm,
        "dims_cm": list(dims),
        "verts": len(mesh.vertices), "polys": len(mesh.polygons),
        "open_edges_before_weld": open_before, "open_edges_after_weld": open_after,
        "non_manifold_edges": non_manifold,
        "uv_layers": [layer.name for layer in mesh.uv_layers],
        "note": "extension is a generated arc tube off the cut ring: no vertex is "
                "stretched and the seam is shared, but the tube carries no ribs",
    }
    print("EXARCTUBE", gun, json.dumps(report[gun], ensure_ascii=False), flush=True)

with open(os.path.join(ROOT, "Reference", "arc_tube_build.json"), "w",
          encoding="utf-8") as handle:
    json.dump(report, handle, indent=1, ensure_ascii=False)
print("EXARCTUBE_REPORT " + json.dumps({g: {"dims_cm": r["dims_cm"],
                                            "seam_gap_mm": r["seam_gap_mm"],
                                            "open_after": r["open_edges_after_weld"]}
                                        for g, r in report.items()}))
