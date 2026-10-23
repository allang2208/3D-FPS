"""Repair the mountain bag shell without changing its UV seams or harness.

The input shell uses UE winding. Convert it to the NumPy author convention
while repairing its legacy normal transform; save.py converts author corners
back to UE. The R3 bounding-box deletion also removed the upper rear wall and
lid. Select complete shoulder-stub islands and close the old strap cuts.
"""
import numpy as np
import trimesh

REVISION = 'UEFrontFaceR6_20261022'
ANCHORS = {
    'top_l': [8.143622965444413, -13.345497744812063, 135.15195703764473],
    'top_r': [-8.09925840379145, -12.327568782081018, 135.2837008925644],
    'bottom_l': [14.482292357434458, -15.626453319715445, 110.12165742954565],
    'bottom_r': [-15.767763043037746, -14.928293735105914, 109.94589019664348],
}


def triangulate_loop(points, forbidden_edges):
    """Minimum-area disk triangulation of a non-planar cut boundary.

    The old roots curl in 3D and can overlap in a best-fit 2D projection.
    Dynamic programming triangulates their ordered boundary directly in 3D,
    without a flat convex hull or a centroid that could sit outside the cut.
    """
    _, _, basis = np.linalg.svd(points-points.mean(0), full_matrices=False)
    flat = (points-points.mean(0)) @ basis[:2].T
    count = len(points)
    cost = np.full((count, count), np.inf)
    split = np.full((count, count), -1, int)
    for i in range(count-1):
        cost[i, i+1] = 0.
    for span in range(2, count):
        for i in range(count-span):
            j = i+span
            for k in range(i+1, j):
                if any(tuple(sorted(e)) in forbidden_edges for e in ((i, k), (k, j), (i, j))):
                    continue
                area = np.linalg.norm(np.cross(points[k]-points[i], points[j]-points[i]))
                if area < 1e-10:
                    continue
                value = cost[i, k]+cost[k, j]+area
                if value < cost[i, j]:
                    cost[i, j], split[i, j] = value, k
    faces = []
    def emit(i, j):
        if j <= i+1:
            return
        k = split[i, j]
        if k < 0:
            raise RuntimeError('Cannot form a finite surface across the cut')
        faces.append([i, k, j])
        emit(i, k)
        emit(k, j)
    emit(0, count-1)
    return np.asarray(faces, int), flat


def repair(source):
    v = np.asarray(source['positions'], float)
    t = np.asarray(source['triangles'], int)
    mesh = trimesh.Trimesh(v, t, process=False)
    islands = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(t)))
    removed = []
    # These complete source islands are the two old shoulder stubs. The main
    # wall, lid and central carry handle extend outside these bounds and stay.
    for ids in islands:
        points = v[t[ids]].reshape(-1, 3)
        low, high = points.min(0), points.max(0)
        if low[2] > 139 and high[2] > 142 and low[1] > -16.5:
            removed.extend(ids)
    keep = np.ones(len(t), bool)
    keep[removed] = False
    # Keep corner attributes attached to the same spatial corner when reversing.
    faces = t[keep][:, [0, 2, 1]]
    uv = np.asarray(source['uv'])[keep][:, [0, 2, 1]]
    normals = np.asarray(source['normals'])[keep][:, [0, 2, 1]] * [-1., -1., 1.]
    normals /= np.maximum(np.linalg.norm(normals, axis=2, keepdims=True), 1e-12)
    bag = dict(source, positions=v.tolist(), triangles=faces.tolist(), uv=uv.tolist(),
               normals=normals.tolist(), triangle_materials=np.asarray(source['triangle_materials'])[keep].tolist())
    # Match coordinates only to trace cut boundaries across split UV vertices.
    # Never weld, average, or remap the authored position/UV/normal/weight arrays.
    _, representative, canonical = np.unique(v.round(4), axis=0, return_index=True, return_inverse=True)
    directed = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    keys = canonical[directed]
    unique_edges, inverse, counts = np.unique(np.sort(keys, axis=1), axis=0, return_inverse=True, return_counts=True)
    occupied_interior = {tuple(edge) for edge, count in zip(unique_edges, counts) if count > 1}
    boundary = keys[counts[inverse] == 1]
    following = {int(b): int(a) for a, b in boundary}  # Opposite the retained edge.
    if len(following) != len(boundary):
        raise RuntimeError('Ambiguous shell boundary; preserve the source')
    loops = []
    remaining = set(following)
    while remaining:
        start = min(remaining)
        loop, node = [], start
        while node not in loop:
            loop.append(node)
            remaining.remove(node)
            node = following[node]
        if node != start:
            raise RuntimeError('Open cut chain; preserve the source')
        loops.append(loop)
    caps = []
    for loop in loops:
        ids = representative[loop]
        points = v[ids]
        # A new diagonal must not reuse a retained interior edge: otherwise a
        # cap can duplicate an adjacent shell triangle and flicker in the game.
        forbidden = {(i, j) for i in range(len(loop)) for j in range(i+1, len(loop))
                     if tuple(sorted((loop[i], loop[j]))) in occupied_interior}
        local, flat = triangulate_loop(points, forbidden)
        first = len(bag['triangles'])
        # A clean canvas patch inside the original atlas, with physical texel
        # density. Existing shell UVs are untouched; no new material or texture.
        patch_uv = flat*.007 + [.17, .87]
        for tri in local:
            coords = points[tri]
            normal = np.cross(coords[1]-coords[0], coords[2]-coords[0])
            normal /= np.linalg.norm(normal)
            bag['triangles'].append(ids[tri].tolist())
            bag['uv'].append(patch_uv[tri].tolist())
            bag['normals'].append([normal.tolist()]*3)
            bag['triangle_materials'].append(0)
        caps.append({'bounds_cm': [points.min(0).tolist(), points.max(0).tolist()],
                     'boundary_vertices': len(loop), 'first_face': first, 'face_count': len(local)})
    used = np.unique(np.asarray(bag['triangles']))
    remap = np.full(len(v), -1, int)
    remap[used] = np.arange(len(used))
    bag['triangles'] = remap[np.asarray(bag['triangles'])].tolist()
    bag['positions'] = v[used].tolist()
    bag['weights'] = [source['weights'][j] for j in used]
    bag.update(anchors=ANCHORS, revision=REVISION, retired_stub_faces=len(removed),
               cut_cap_faces=sum(c['face_count'] for c in caps), shell_caps=caps,
               shell_contract='Original upper wall and lid restored; outward winding and transformed split normals; six closed legacy strap cuts')
    return bag
