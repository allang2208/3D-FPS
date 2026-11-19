"""Lay out the carpenter's inherited cloth and boot patterns in rest-space centimetres."""

import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu


def _pattern_vertices(faces, uv):
    # The donor already has side seams, inseams, pocket cuts and separate boot uppers.
    # A geometric vertex can have a different pattern coordinate on each side of a cut.
    keys = np.column_stack((faces.ravel(), uv.reshape(-1, 2)))
    corners, inverse = np.unique(keys, axis=0, return_inverse=True)
    return corners[:, 0].astype(np.intp), corners[:, 1:], inverse.reshape(faces.shape)


def _relax(points, donor, triangles, repeat_cm, straighten_legs):
    """Fit the donor's cut pieces to the surface metric, retaining their seams and grain."""
    first = triangles.ravel()
    second = triangles[:, [1, 2, 0]].ravel()
    n = len(donor)
    graph = coo_matrix((np.ones(len(first)), (first, second)), shape=(n, n)).tocsr()
    count, piece = connected_components(graph, directed=False)
    face_piece = piece[triangles[:, 0]]

    # Express each triangle's true edge lengths and included angles in its tangent plane.
    # The longest edge provides a stable basis even on narrow rolled edges.
    q = points[triangles]
    edges = q[:, [1, 2, 0]] - q
    length_sq = np.einsum('fij,fij->fi', edges, edges)
    t = edges[np.arange(len(q)), length_sq.argmax(axis=1)]
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
    normal = np.cross(edges[:, 0], -edges[:, 2])
    area2 = np.linalg.norm(normal, axis=1)
    across = np.cross(normal / np.maximum(area2[:, None], 1e-12), t)
    local = np.stack((np.einsum('fij,fj->fi', edges, t),
                      np.einsum('fij,fj->fi', edges, across)), axis=-1)

    source = donor[triangles]
    e1, e2 = source[:, 1] - source[:, 0], source[:, 2] - source[:, 0]
    signed_area = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
    signed_sum = np.bincount(face_piece, signed_area, minlength=count)
    local[:, :, 1] *= np.where(signed_sum[face_piece] < 0, -1., 1.)[:, None]
    physical_area = np.bincount(face_piece, area2, minlength=count)
    uv_area = np.bincount(face_piece, np.abs(signed_area), minlength=count)
    scale = np.sqrt(np.divide(physical_area, uv_area, out=np.ones(count), where=uv_area > 1e-12))

    # Start from the cut pattern's placement. A weak positional term keeps very small
    # trims and disconnected pieces anchored while curvature relaxes within each island.
    area_per_vertex = np.bincount(first, np.repeat(area2 / 6., 3), minlength=n)
    mass = np.maximum(area_per_vertex, 1e-10)
    piece_mass = np.bincount(piece, mass, minlength=count)

    def means(values):
        return np.stack([np.bincount(piece, mass * column, minlength=count) / piece_mass
                         for column in values.T], axis=1)

    center = means(donor)
    reference = (donor - center[piece]) * scale[piece, None]
    uv_cm = reference.copy()
    stiffness = np.minimum(area2[:, None] / np.maximum(length_sq, 1e-10), 12.)
    weights = stiffness.ravel()
    boundary_weight = mass / 24.**2 + 1e-10
    off_diagonal = coo_matrix((-weights, (first, second)), shape=(n, n)).tocsc()
    diagonal = (np.bincount(first, weights, minlength=n)
                + np.bincount(second, weights, minlength=n) + boundary_weight)
    system = splu((off_diagonal + off_diagonal.T + diags(diagonal)).tocsc())

    # Alternate a best rigid rotation per triangle with a shared-vertex solve. Surface
    # lengths supply both UV derivatives, including the top of the shoulder and boot toe.
    for _ in range(8):
        current = (uv_cm[second] - uv_cm[first]).reshape(-1, 3, 2)
        dot = np.sum(stiffness * np.einsum('fij,fij->fi', local, current), axis=1)
        cross = np.sum(stiffness * (local[:, :, 0] * current[:, :, 1]
                                    - local[:, :, 1] * current[:, :, 0]), axis=1)
        angle = np.arctan2(cross, dot)
        cos, sin = np.cos(angle)[:, None], np.sin(angle)[:, None]
        rotated = np.stack((cos * local[:, :, 0] - sin * local[:, :, 1],
                            sin * local[:, :, 0] + cos * local[:, :, 1]), axis=-1)
        target = (stiffness[:, :, None] * rotated).reshape(-1, 2)
        rhs = boundary_weight[:, None] * reference
        for k in range(2):
            rhs[:, k] += (np.bincount(second, target[:, k], minlength=n)
                          - np.bincount(first, target[:, k], minlength=n))
        uv_cm = system.solve(rhs)

    uv_cm -= means(uv_cm)[piece]
    phase = np.mod(center, 1.)
    if straighten_legs:
        # The four long front/back leg panels share an upright warp and a waist-level
        # crossgrain datum. Short pockets, fly, loops and waistband keep their own grain.
        z = points[:, 2]
        low, high = np.full(count, np.inf), np.full(count, -np.inf)
        np.minimum.at(low, piece, z)
        np.maximum.at(high, piece, z)
        z_mean = means(z[:, None])[:, 0]
        down = means(uv_cm * (z_mean[piece] - z)[:, None])
        direction = down / np.maximum(np.linalg.norm(down, axis=1, keepdims=True), 1e-10)
        long_piece = high - low > 35.
        along = long_piece[piece]
        dx, dy = direction[piece[along]].T
        u, v = uv_cm[along].T
        uv_cm[along] = np.column_stack((dy * u - dx * v, dx * u + dy * v))
        phase[long_piece, 1] = (high.max() - z_mean[long_piece]) / repeat_cm
    return (uv_cm / repeat_cm + phase[piece])[triangles]


def garment_uv(name, points, faces, existing_uv, material_ids):
    """Return (triangle, corner, uv) coordinates in the supplied part-local face order."""
    patterns = {
        'trousers': ((1,), 20.),
        'Continuous linen shirt': ((0,), 20.),
        'boots': ((4, 5), 19.),
    }
    donor = np.asarray(existing_uv, dtype=np.float64)
    if name not in patterns:
        # Belt, collar, placket and rolled sleeves were already cut in centimetres.
        return donor
    materials, repeat_cm = patterns[name]
    faces = np.asarray(faces, dtype=np.intp)
    material_ids = np.broadcast_to(material_ids, (len(faces),))
    selected = np.isin(material_ids, materials)
    if not np.any(selected):
        return donor
    vertices, pattern, triangles = _pattern_vertices(faces[selected], donor[selected])
    result = donor.copy()
    result[selected] = _relax(np.asarray(points, dtype=np.float64)[vertices], pattern,
                              triangles, repeat_cm, name == 'trousers')
    return result
