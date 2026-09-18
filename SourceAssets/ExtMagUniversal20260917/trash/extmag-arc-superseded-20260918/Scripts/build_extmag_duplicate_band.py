"""Rebuild the M4 and QBZ extended magazines by repeating a clean body band.

Why this build exists (2026-09-18, round 5):
  * the earlier "stretch a band" builds deformed the magazine body. On the M4
    the deformed band sat exactly in the reload animation's left-hand grip
    zone (the hand then no longer read as gripping the magazine), and on the
    QBZ the arc variant moved everything below the band with a hard switch, so
    the surface folded at the band ("the model is wrong").

What it does instead - no vertex is ever stretched:
  1. cut the magazine at `band_bottom` and `band_bottom + EXTENSION`;
  2. keep everything above `band_bottom` exactly as authored (so the insertion
     section and the whole grip zone stay factory geometry);
  3. repeat the clean band that sits between the two cuts, one extension lower,
     and move everything below `band_bottom` down by the same amount, using the
     rigid transform that maps the band's own lower ring onto its upper ring
     (so the extension follows whatever curvature the factory part really has:
     a plain shift for a straight magazine, an arc for a curved one);
  4. weld the three rings so the result is one closed shell again.

Round 6 (2026-09-18, after the user reported "the 191 and M4 magazine models have a
wrong truncation"): the copy transform now comes from rigidly registering the
band's own two cut rings (lower ring -> upper ring) instead of a direction fitted
to the surface. The fitted direction was a couple of degrees off, and over a 6 cm
band that shifted the whole lower half sideways by a few millimetres - it read as
a magazine that had been cut and glued back crooked. Ring registration pins the
seam (seam_rms_mm ~ 0) and reports the part's real curvature as band_bend_deg.

Run: blender -b -P build_extmag_duplicate_band.py
"""
import bmesh
import bpy
import json
import math
import os
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FBXDIR = os.path.join(ROOT, "FBX")
SA = r"D:\FPS3D\FPSGAME\SourceAssets"
BLENDS = os.path.join(SA, "PhantomRearGripIntegration20260913")

EXTENSION = 0.06          # 6 cm of extra magazine
BAND_BOTTOM = 0.018       # band starts 1.8 cm above the factory floor plate
STITCH_HEIGHT = 0.025     # the seam correction fades out over this much copy
SHELL_WELD = 1e-5         # 0.01 mm

JOBS = {
    "M4": dict(source=os.path.join(SA, "M4HK416Replica20260910",
                                   "SK_M4_FoldingSights_HK416.fbx"),
               match="magazine", out="SM_ExtMag_M440_dupb.fbx",
               band_bottom=0.030),
    "QBZ": dict(source=os.path.join(BLENDS, "QBZ191", "SK_QBZ191_Manny.fbx"),
                match="magazine", out="SM_ExtMag_QBZ40_dupb.fbx",
                band_bottom=0.030),
}


def load_source(cfg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=cfg["source"])


def pick_object(cfg):
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            for material in ob.data.materials:
                if material and cfg["match"] in material.name.lower():
                    return ob
    raise RuntimeError("magazine object not found in " + cfg["source"])


def keep_magazine_slot(ob, match):
    index = next((i for i, m in enumerate(ob.data.materials)
                  if m and match in m.name.lower()), None)
    if index is None:
        raise RuntimeError("no magazine material slot on " + ob.name)
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


def kabsch(source, target):
    """Rigid transform (R, t) that maps `source` points onto `target` points."""
    source_centre = source.mean(axis=0)
    target_centre = target.mean(axis=0)
    covariance = (source - source_centre).T @ (target - target_centre)
    u, _, vt = np.linalg.svd(covariance)
    flip = np.sign(np.linalg.det(vt.T @ u.T))
    corrections = np.diag([1.0, 1.0, flip])
    rotation = vt.T @ corrections @ u.T
    translation = target_centre - rotation @ source_centre
    return rotation, translation


def band_axis(mesh, low_value, high_value, centroid, axis):
    """The magazine body's own axis inside a slice of the part.

    A tube's surface normals are perpendicular to its axis, so the axis is the
    least-variance direction of the face normals - measured on the factory
    geometry itself, with no assumed circle and no vertex correspondence.
    """
    normals = np.array([[p.normal.x, p.normal.y, p.normal.z] for p in mesh.polygons
                        if low_value <= (p.center - centroid).dot(axis) < high_value])
    if len(normals) < 24:
        raise RuntimeError("band has too few faces for an axis estimate: %d" % len(normals))
    covariance = normals.T @ normals
    values, vectors = np.linalg.eigh(covariance)
    direction = Vector((float(vectors[0, 0]), float(vectors[0, 1]), float(vectors[0, 2])))
    if direction.length < 1e-9:
        return axis
    direction.normalize()
    if direction.dot(axis) < 0.0:
        direction = -direction
    return direction


def band_transform(verts, centroid, axis, band_bottom, height):
    """Direction along which the factory body repeats itself.

    The band is shifted one band-height along a candidate direction and measured
    against the magazine's own body above it; the direction with the smallest
    mean distance is the continuation the factory part actually has. That
    captures the magazine's tilt in the rifle frame (the M4 magazine hangs
    several degrees forward) without a circle fit, a plane guess or any vertex
    correspondence, and the ribs line up because the surface is what is scored.
    """
    def collect(low_value, high_value):
        return np.array([[v.co.x, v.co.y, v.co.z] for v in verts
                         if low_value <= (v.co - centroid).dot(axis) < high_value])

    band = collect(band_bottom, band_bottom + height)
    body = collect(band_bottom + height, band_bottom + 2.0 * height)
    if len(band) < 32 or len(body) < 32:
        raise RuntimeError("band/body too sparse (%d / %d)" % (len(band), len(body)))
    band = band[::max(1, len(band) // 220)]
    body = body[::max(1, len(body) // 700)]

    def cost(tilt_x, tilt_y):
        direction = np.array([math.tan(tilt_x), math.tan(tilt_y), 1.0])
        direction /= np.linalg.norm(direction)
        moved = band + direction * height
        distances = ((moved[:, None, :] - body[None, :, :]) ** 2).sum(axis=2)
        return float(np.sqrt(distances.min(axis=1)).mean())

    span = math.radians(20.0)
    best = None
    while span > math.radians(0.15):
        step = span / 8.0
        centre = (0.0, 0.0) if best is None else (best[1], best[2])
        for i in range(-8, 9):
            for j in range(-8, 9):
                tx = centre[0] + i * step
                ty = centre[1] + j * step
                score = cost(tx, ty)
                if best is None or score < best[0]:
                    best = (score, tx, ty)
        span /= 4.0

    direction = Vector((math.tan(best[1]), math.tan(best[2]), 1.0)).normalized()
    drift = direction * height
    tilt = math.degrees(math.atan2(math.hypot(drift.x, drift.y), height))
    return (Matrix.Identity(3), drift, 0.0, direction, float(tilt),
            float(best[0]), (drift.x, drift.y))


def ring_verts(bm, centroid, axis, value, tol=1e-4):
    return [v for v in bm.verts
            if abs((v.co - centroid).dot(axis) - value) < tol]


def plane_ring(bm, origin, normal, tol=1e-4):
    """Vertices the bisect left exactly on that plane, as plain coordinates."""
    return [v.co.copy() for v in bm.verts
            if abs((v.co - origin).dot(normal)) < tol]


def ordered_ring(bm, origin, normal, tol=1e-4):
    """The outside wall's loop on that plane, walked in ring order.

    A cut through a hollow magazine leaves more than one loop (outer wall plus
    the cavity opening). Only the outer wall is the surface the player sees, and
    the two are told apart by perimeter - sorting by vertex count picks the cavity
    wall on a body whose ribs carry more vertices than its outer corners. The
    vertices come back in order so the seam can be pinned onto the polyline.
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

    def ring_edges(group):
        members = set(group)
        return [edge for edge in {edge for vert in group for edge in vert.link_edges}
                if edge.verts[0] in members and edge.verts[1] in members]

    if not loops:
        return []
    def perimeter(group):
        return sum(e.calc_length() for e in ring_edges(group))

    def offset(group):
        centre = np.mean([[v.co.x, v.co.y, v.co.z] for v in group], axis=0)
        return float(np.linalg.norm(centre - np.array([origin.x, origin.y, origin.z])))

    # A plane that grazes a rib leaves a long snaking loop; it is off the
    # magazine's axis, so keep the loops that sit on the axis and take the biggest
    # of those. Without the filter the QBZ picked a loop 40% too wide.
    on_axis = [group for group in loops if offset(group) <= 0.015]
    loops = on_axis or loops
    if os.environ.get("DUPBAND_RING_DEBUG"):
        print("DUPBAND_RINGDEBUG", [(len(g), round(perimeter(g) * 100, 2), round(offset(g) * 100, 2))
                                    for g in loops[:4]], flush=True)
    loop = max(loops, key=perimeter)
    # Order by angle around the loop's own centre instead of walking the edges: a
    # cut that touches a rib can leave a loop that is not a simple cycle, and a
    # truncated walk (5 of 118 vertices) is worse than no walk at all. A magazine
    # cross-section is convex enough that the angular order is the ring order.
    centre = Vector(np.mean([[v.co.x, v.co.y, v.co.z] for v in loop], axis=0).tolist())
    helper = Vector((0.0, 0.0, 1.0)) if abs(normal.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    first = normal.cross(helper).normalized()
    second = normal.cross(first).normalized()

    def bearing(vert):
        offset = vert.co - centre
        return math.atan2(offset.dot(second), offset.dot(first))

    return [vert.co.copy() for vert in sorted(loop, key=bearing)]


def register_rings(source, target, iterations=25):
    """Rigid transform (R, t) with R @ source + t ~ target, plus its RMS error.

    Nearest-point ICP between the band's two cut rings. Both rings are cut
    perpendicular to the magazine's own centreline, so they are the same
    cross-section and the registration converges to a fraction of a millimetre -
    that is what actually closes the seam and what carries a curved magazine's
    bend (the previous direction fit could only translate).
    """
    source_points = np.array([[p.x, p.y, p.z] for p in source])
    target_points = np.array([[p.x, p.y, p.z] for p in target])
    # The two bisects rarely leave the same number of vertices, so start from a
    # plain centroid translation and let the nearest-point loop build the pairs.
    rotation = np.eye(3)
    translation = target_points.mean(axis=0) - source_points.mean(axis=0)
    for _ in range(iterations):
        moved = (source_points @ rotation.T) + translation
        nearest = target_points[((moved[:, None, :] - target_points[None, :, :]) ** 2)
                                .sum(axis=2).argmin(axis=1)]
        rotation, translation = kabsch(source_points, nearest)
    moved = (source_points @ rotation.T) + translation
    distances = np.sqrt(((moved[:, None, :] - target_points[None, :, :]) ** 2)
                        .sum(axis=2).min(axis=1))
    return (Matrix(rotation.tolist()), Vector(translation.tolist()),
            float(np.sqrt((distances ** 2).mean())))


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


def rib_pitch(points, centroid, axis, low, high, bins=160):
    """Pitch of the magazine's repeating body detail (its ribs).

    The band that gets repeated has to be a whole number of pitches tall,
    otherwise the ribs change phase at the seam and the eye reads a step even
    though the surface is continuous. The per-slice spread of the body is
    periodic, so autocorrelating it recovers the pitch.
    """
    count = np.zeros(bins)
    for index in range(bins):
        a = low + (high - low) * index / bins
        b = low + (high - low) * (index + 1) / bins
        slab = [p for p in points if a <= (p - centroid).dot(axis) < b]
        if not slab:
            continue
        xs = [p.x for p in slab]
        ys = [p.y for p in slab]
        count[index] = (max(xs) - min(xs)) + (max(ys) - min(ys))
    signal = count - count.mean()
    if np.allclose(signal, 0.0):
        return (high - low) / 4.0, 0.0
    correlation = np.correlate(signal, signal, mode="full")[len(signal) - 1:]
    step = (high - low) / bins
    best_lag = 0
    best_value = -1.0
    for lag in range(3, len(correlation) // 3):
        if correlation[lag] > best_value:
            best_value = correlation[lag]
            best_lag = lag
    pitch = best_lag * step
    strength = float(best_value / correlation[0]) if correlation[0] else 0.0
    return pitch, strength


report = {}
for gun, cfg in JOBS.items():
    load_source(cfg)
    source = pick_object(cfg)
    mesh = source.data.copy()
    mesh.name = "SM_ExtMag_%s" % gun
    ob = bpy.data.objects.new("SM_ExtMag_%s" % gun, mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = source.matrix_world.copy()
    for modifier in list(ob.modifiers):
        ob.modifiers.remove(modifier)
    for other in [o for o in bpy.context.scene.objects if o is not ob]:
        bpy.data.objects.remove(other, do_unlink=True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    keep_magazine_slot(ob, cfg["match"])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    points = [ob.matrix_world @ v.co for v in mesh.vertices]
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    centroid = (lo + hi) * 0.5
    size = hi - lo
    axis_index = int(np.argmax(size))
    thin_index = int(np.argmin(size))
    axis = Vector((0.0, 0.0, 0.0))
    axis[axis_index] = 1.0

    samples, low, high = slice_centres(points, centroid, axis)
    factory_cm = round((high - low) * 100, 2)

    band_bottom = low + cfg.get("band_bottom", BAND_BOTTOM)
    pitch, pitch_strength = rib_pitch(points, centroid, axis, low, high)
    repeats = max(1, int(round(EXTENSION / pitch))) if pitch > 1e-4 else 1
    band_height = pitch * repeats if pitch > 1e-4 else EXTENSION
    if band_height < 0.02 or band_height > 0.09:
        band_height = EXTENSION
    if band_bottom + band_height >= high:
        raise RuntimeError("%s factory magazine is too short for a %.0f cm band"
                           % (gun, EXTENSION * 100))
    print("DUPBAND_DEBUG", gun, "rib_pitch_cm", round(pitch * 100, 3),
          "pitch_strength", round(pitch_strength, 3),
          "band_height_cm", round(band_height * 100, 3), flush=True)

    # Cut the band perpendicular to the magazine's OWN axis. A bounding-box cut is
    # oblique on a raked or curved body, and oblique rings are not congruent, so
    # no transform could land the copy exactly on the seam - that is the "wrong
    # truncation" the user saw in round 5 (the lower half was shifted sideways,
    # and on the curved QBZ skewed as well). The axis is measured from the band's
    # own face normals (a tube's normals are perpendicular to its axis, so the
    # least-variance direction of the normals is the axis); a centreline fitted
    # from slice centroids wobbles with the ribs and left this 3 mm off.
    centreline = sorted(((value, point.copy()) for value, point in samples),
                        key=lambda item: item[0])

    # Fit the centreline as quadratics of the axial coordinate. That yields both
    # the band plane origins and their tangents; a tangent taken from raw slice
    # centroids (or from a slab of face normals) is far too noisy here - it put
    # the lower cut plane 79 degrees off the magazine's own axis, which cuts a
    # 13 cm sliver instead of a cross-section.
    centre_values = np.array([value for value, _ in centreline])
    centre_points = np.array([[p.x, p.y, p.z] for _, p in centreline])
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

    high_value = band_bottom + band_height
    low_origin, high_origin = point_at(band_bottom), point_at(high_value)
    low_normal, high_normal = tangent_at(band_bottom), tangent_at(high_value)
    print("DUPBAND_DEBUG", gun, "cut_normals_vs_axis_deg",
          round(math.degrees(low_normal.angle(axis)), 2),
          round(math.degrees(high_normal.angle(axis)), 2), flush=True)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    for label, plane_co, plane_no in (("low", low_origin, low_normal),
                                      ("high", high_origin, high_normal)):
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=plane_co, plane_no=plane_no,
                               clear_inner=False, clear_outer=False)
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        box = [(min(v.co[i] for v in bm.verts), max(v.co[i] for v in bm.verts)) for i in range(3)]
        print("DUPBAND_DEBUG", gun, "after_bisect_" + label,
              "bbox_cm", [round((box[i][1] - box[i][0]) * 100, 2) for i in range(3)],
              "verts", len(bm.verts), flush=True)

    low_ring = ordered_ring(bm, low_origin, low_normal)
    high_ring = ordered_ring(bm, high_origin, high_normal)
    if len(low_ring) < 8 or len(high_ring) < 8:
        raise RuntimeError("%s cut rings too sparse (low %d / high %d)"
                           % (gun, len(low_ring), len(high_ring)))
    # The copy is one arc step of the band: rotate it by the bend the factory body
    # has across the band (so a curved magazine's extension keeps bending) and land
    # its upper ring on the lower ring. A pure translation fit is what skewed the
    # QBZ in round 5; whatever millimetres of taper are left over are taken out by
    # the stitch, which is also what welds the seam shut.
    fit_method = "arc-step"
    bend_axis = low_normal.cross(high_normal)
    if bend_axis.length < 1e-6:
        bend_axis = Vector((1.0, 0.0, 0.0))
        bend_deg = 0.0
    else:
        bend_axis.normalize()
        bend_deg = math.degrees(low_normal.angle(high_normal))

    def ring_centre(ring):
        return Vector(np.array([[p.x, p.y, p.z] for p in ring]).mean(axis=0).tolist())

    _, _, ring_fit_rms = register_rings(high_ring, low_ring)
    for label, ring in (("low", low_ring), ("high", high_ring)):
        blob = np.array([[p.x, p.y, p.z] for p in ring])
        extents = sorted((blob.max(axis=0) - blob.min(axis=0)).tolist(), reverse=True)
        print("DUPBAND_DEBUG", gun, "ring_" + label, "verts", len(ring),
              "extent_cm", [round(float(e) * 100, 2) for e in extents], flush=True)
    print("DUPBAND_DEBUG", gun, "ring_fit_rms_mm", round(ring_fit_rms * 1000, 3),
          "low_ring", len(low_ring), "high_ring", len(high_ring), flush=True)

    copy_rotation = Matrix.Rotation(-math.radians(bend_deg), 4, bend_axis)
    high_centre, low_centre = ring_centre(high_ring), ring_centre(low_ring)
    # No scale correction: the mean radius of a ring depends on how its vertices
    # are distributed along the walls (the QBZ read 1.40 for rings whose extents
    # differ by 13%), and inflating the copy by that made the seam pin worse, not
    # better. The stitch takes the real difference out.
    ring_scale = 1.0

    def moved(point):
        return copy_rotation @ ((point - high_centre) * ring_scale) + low_centre

    band_faces = []
    lower_faces = []
    for face in bm.faces:
        centre = face.calc_center_median()
        if (centre - high_origin).dot(high_normal) >= 0.0:
            continue
        if (centre - low_origin).dot(low_normal) >= 0.0:
            band_faces.append(face)
        else:
            lower_faces.append(face)
    if not band_faces or not lower_faces:
        raise RuntimeError("%s cut produced no band/lower faces" % gun)

    # 1. copy the band and the base-plate section (separately, so neither copy
    #    shares boundary vertices with the geometry that stays in place) and
    #    move both copies down along the magazine's own direction.
    copies = []
    for group in (band_faces, lower_faces):
        duplicate = bmesh.ops.duplicate(bm, geom=group)
        verts = [element for element in duplicate["geom"]
                 if isinstance(element, bmesh.types.BMVert)]
        seam = [vert for vert in verts
                if abs((vert.co - high_origin).dot(high_normal)) < 1e-4]
        for vert in verts:
            vert.co = moved(vert.co)
        if group is band_faces:
            band_copy = verts
            band_seam = seam
        copies.append(len(verts))

    # 2. stitch the copy's upper ring onto the band's lower ring. The two are the
    #    same cross-section but not the same vertex list - the bisects land on
    #    different triangles and the body tapers a fraction of a millimetre - so
    #    the seam ring is pinned onto the lower ring's polyline (not onto its
    #    vertices, which would collapse it) and that correction fades out over the
    #    last STITCH_HEIGHT of the copy. The ribs keep their own pitch and the
    #    seam is closed instead of stepped.
    def polyline_target(point):
        best, best_distance = None, None
        for index in range(len(low_ring)):
            start = low_ring[index]
            span = low_ring[(index + 1) % len(low_ring)] - start
            if span.length_squared < 1e-12:
                candidate = start
            else:
                t = max(0.0, min(1.0, (point - start).dot(span) / span.length_squared))
                candidate = start + span * t
            distance = (candidate - point).length_squared
            if best_distance is None or distance < best_distance:
                best, best_distance = candidate, distance
        return best

    stitch_max = 0.0
    stitch_total = 0.0
    corrections = {}
    for vert in band_seam:
        target = polyline_target(vert.co)
        corrections[vert] = target - vert.co
        vert.co = target
        stitch_max = max(stitch_max, corrections[vert].length)
        stitch_total += corrections[vert].length
    for vert in band_copy:
        if vert in corrections:
            continue
        height = (vert.co - low_origin).dot(low_normal) + band_height
        weight = min(1.0, max(0.0, (height - (band_height - STITCH_HEIGHT)) / STITCH_HEIGHT))
        if weight <= 0.0:
            continue
        weight = weight * weight * (3.0 - 2.0 * weight)
        nearest = min(corrections, key=lambda seed: (seed.co - vert.co).length_squared)
        vert.co = vert.co + corrections[nearest] * weight
    stitch_max_mm = round(stitch_max * 1000.0, 4)
    stitch_mean_mm = round(stitch_total / max(1, len(corrections)) * 1000.0, 4)
    ring_separation_cm = round((high_centre - low_centre).length * 100, 3)
    print("DUPBAND_DEBUG", gun, "fit", fit_method,
          "low_ring", len(low_ring), "high_ring", len(high_ring),
          "band_faces", len(band_faces), "band_height_cm", round(band_height * 100, 3),
          "ring_separation_cm", ring_separation_cm, "bend_deg", round(bend_deg, 3),
          "stitch_max_mm", stitch_max_mm, "stitch_mean_mm", stitch_mean_mm,
          "seam_verts", len(corrections), flush=True)
    if stitch_max_mm > 8.0:
        raise RuntimeError("%s seam stitch would move %.2f mm - the cut rings do not "
                           "match" % (gun, stitch_max_mm))

    # 3. drop the original base-plate section: the moved copy replaces it.
    bmesh.ops.delete(bm, geom=lower_faces, context='FACES')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    duplicate = {"geom": []}

    open_before = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    debug_pts = [v.co.copy() for v in bm.verts]
    print("DUPBAND_DEBUG", gun, "after_move_bbox_cm",
          [round((max(p[i] for p in debug_pts) - min(p[i] for p in debug_pts)) * 100, 2) for i in range(3)],
          "band_faces", len(band_faces), "lower_faces", len(lower_faces),
          "duplicated", len([e for e in duplicate["geom"] if isinstance(e, bmesh.types.BMVert)]), flush=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=SHELL_WELD)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    open_after = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    non_manifold = sum(1 for edge in bm.edges if len(edge.link_faces) > 2)
    bm.free()
    mesh.update()

    new_points = [ob.matrix_world @ v.co for v in mesh.vertices]
    nlo = Vector((min(p.x for p in new_points), min(p.y for p in new_points), min(p.z for p in new_points)))
    nhi = Vector((max(p.x for p in new_points), max(p.y for p in new_points), max(p.z for p in new_points)))
    dims = tuple(round((nhi - nlo)[i] * 100, 2) for i in range(3))

    out = os.path.join(FBXDIR, cfg["out"])
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={'MESH'},
                             axis_forward='-Y', axis_up='Z', bake_anim=False,
                             mesh_smooth_type='FACE', use_tspace=True)

    report[gun] = {
        "source": cfg["source"], "file": out,
        "factory_length_cm": factory_cm, "dims_cm": list(dims),
        "band_bottom_cm_above_floor": round(BAND_BOTTOM * 100, 2),
        "cut_cm_above_floor": round(((high_origin - centroid).dot(axis) - band_bottom) * 100, 2),
        "rib_pitch_cm": round(pitch * 100, 3),
        "band_height_cm": round(band_height * 100, 3),
        "ring_separation_cm": ring_separation_cm,
        "band_bend_deg": round(bend_deg, 3),
        "fit_method": fit_method,
        "stitch_max_mm": stitch_max_mm,
        "stitch_mean_mm": stitch_mean_mm,
        "rigid_move": "shift" if bend_deg < 0.2 else "arc",
        "verts": len(mesh.vertices), "polys": len(mesh.polygons),
        "open_edges_before_weld": open_before, "open_edges_after_weld": open_after,
        "non_manifold_edges": non_manifold,
        "uv_layers": [layer.name for layer in mesh.uv_layers],
    }
    print("DUPBAND", gun, json.dumps(report[gun], ensure_ascii=False), flush=True)

with open(os.path.join(ROOT, "Reference", "duplicate_band_build.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=1, ensure_ascii=False)
print("DUPBAND_REPORT " + json.dumps(report, ensure_ascii=False), flush=True)
