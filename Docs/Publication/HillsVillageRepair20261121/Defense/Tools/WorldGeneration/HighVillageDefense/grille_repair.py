"""Fit the original wrought-iron grid in its 875 x 495 cm authoring space."""
import numpy as np

from source_mesh import Surface


# Midpoints between the eight horizontal bars and the top lifting beam.
ROW_LIMITS = np.array([61., 105., 150., 196., 240., 284., 330., 379.])


def slice_x(mesh, left, right):
    return mesh.clipped(lambda p: p[:, 0] - left).clipped(lambda p: right - p[:, 0])


def fill_missing_links(mesh):
    # This intact length between the two adjacent riveted posts carries the
    # same forge marks, UVs and thickness as the rest of the fifth rail.
    donor = slice_x(mesh, -162., -133.)
    donor = donor.clipped(lambda p: p[:, 2] - 198.).clipped(lambda p: 235. - p[:, 2])
    for left, right in ((-72., -27.), (27., 71.), (322., 372.)):
        positions = donor.pos.copy()
        positions[:, 0] = left + (positions[:, 0] + 162.) * (right - left) / 29.
        yield donor.moved(positions)


def cap_cut(mesh, x):
    """Seal each separate bar end with its own cap, retaining the cut-edge UVs."""
    on_plane = np.isclose(mesh.pos[:, 0], x, rtol=0., atol=1e-7)
    cut_faces = mesh.faces[np.sum(on_plane[mesh.faces], axis=1) == 2]
    edges = []
    for a, b, c in cut_faces:
        for start, end in ((a, b), (b, c), (c, a)):
            if on_plane[start] and on_plane[end]:
                edges.append((end, start))
    if not edges:
        return mesh
    edges = np.asarray(edges)
    row = np.searchsorted(ROW_LIMITS, mesh.pos[edges, 2].mean(axis=1))
    positions, uvs, triangles = [], [], []
    for index in np.unique(row):
        rim_edges = edges[row == index]
        rim = np.unique(rim_edges)
        center = len(mesh.pos) + len(positions)
        positions.append((mesh.pos[rim].min(axis=0) + mesh.pos[rim].max(axis=0)) * .5)
        uvs.append(mesh.uv[rim].mean(axis=0))
        triangles.append(np.column_stack((rim_edges, np.full(len(rim_edges), center))))
    return Surface(np.vstack((mesh.pos, positions)), np.vstack([mesh.faces, *triangles]),
                   np.vstack((mesh.uv, uvs)))


def joined_east_grid(mesh):
    # Keep the lifting eyes, spikes and original side spacing. The nine
    # individual joins sit halfway along open bays, away from upright posts.
    rims = []
    for side in (-1, 1):
        cut_x = side * 104.
        half = mesh.clipped(lambda p: side * p[:, 0] - 104.)
        # Include intersections inside long triangles and across UV islands.
        rims.append(half.pos[np.isclose(half.pos[:, 0], cut_x, rtol=0., atol=1e-7)])
        half = cap_cut(half, cut_x)
        yield half.moved(half.pos - [side * 100., 0., 0.])

    # A short lapped splice bridges the 8 cm clear gap on each rail. Its
    # profile follows each receiving end, so the joint also works on the
    # deeper lifting beam. The bearing ends are capped inside the overlap.
    donor_x = -150.
    lap = slice_x(mesh, donor_x - 8., donor_x + 8.)
    lap = cap_cut(cap_cut(lap, donor_x - 8.), donor_x + 8.)
    positions = lap.pos.copy()
    positions[:, 0] -= donor_x
    source_rows = np.searchsorted(ROW_LIMITS, lap.pos[:, 2])
    for row in np.unique(source_rows):
        selected = source_rows == row
        original = lap.pos[selected, 1:]
        origin = (original.min(axis=0) + original.max(axis=0)) * .5
        radius = np.ptp(original, axis=0) * .5
        targets = []
        for rim in rims:
            section = rim[np.searchsorted(ROW_LIMITS, rim[:, 2]) == row, 1:]
            targets.append(((section.min(axis=0) + section.max(axis=0)) * .5,
                            np.ptp(section, axis=0) * .5))
        x = positions[selected, 0]
        t = np.clip((x + 4.) / 8., 0., 1.)[:, None]
        center = targets[0][0] * (1. - t) + targets[1][0] * t
        target_radius = targets[0][1] * (1. - t) + targets[1][1] * t
        # The subtly proud forged band tapers into the parent iron at both
        # ends, leaving no coincident broad faces at the overlap.
        allowance = np.interp(abs(x), [0., 4.8, 8.], [.75, .75, -.7])[:, None]
        positions[selected, 1:] = center + (original - origin) / radius * (target_radius + allowance)
    yield lap.moved(positions)
