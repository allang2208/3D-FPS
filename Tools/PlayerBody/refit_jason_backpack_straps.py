"""Reform only the two native shoulder ribbons against the equipped shirt envelope.

All original triangles, UVs and material assignments are retained. Longitudinal
sections share a smooth frame and skin weights instead of projecting individual
vertices onto the nude body (which flattened and corrugated the old straps).
"""
import json
import shutil
from pathlib import Path

import numpy as np
import trimesh
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

PROJECT = Path('D:/FPS3D/FPSGAME')
INPUT = PROJECT / 'SourceAssets/JasonPlayer20261003'
ROOT = PROJECT / 'SourceAssets/JasonEquipmentRepair20261003'
REVISION = ROOT / 'ShoulderStraps'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def unit(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-9)


def smoothstep(a):
    a = np.clip(a, 0., 1.)
    return a * a * (3. - 2. * a)


def make_envelope(target):
    # Include the actual saved fits, including their folds and neckline, rather
    # than assuming that a constant offset from skin clears every garment.
    vertices, triangles, weights = [], [], []
    count = 0
    for key in ['Jason', 'ue_field_sweater', 'ue_field_sweater_charcoal', 'ue_chainmail_shirt']:
        source = target if key == 'Jason' else read(INPUT / (key + '.json'))
        fitted = source if key == 'Jason' else read(INPUT / (key + '_fitted.json'))
        v = np.asarray(fitted['positions'])
        t = np.asarray(source['triangles'], dtype=int)
        materials = np.asarray(source['triangle_materials'])
        if key == 'Jason':
            keep = materials == 2
        else:
            keep = np.isin(materials, [i for i, m in enumerate(fitted['materials'])
                                       if not m['slot'].startswith('Exposed')])
        # Hands, forearms and the skirt do not define a shoulder strap surface.
        centers = v[t].mean(axis=1)
        keep &= (centers[:, 2] > 98.) & (np.abs(centers[:, 0]) < 23.)
        triangles.append(t[keep] + count)
        vertices.append(v)
        dense = np.zeros((len(v), len(target['bones'])))
        for i, pairs in enumerate(fitted['weights']):
            for bone, weight in pairs:
                dense[i, bone] += weight
        weights.append(dense)
        count += len(v)
    return (trimesh.Trimesh(np.vstack(vertices), np.vstack(triangles), process=False),
            np.vstack(weights))


def refit():
    REVISION.mkdir(parents=True, exist_ok=True)
    before = REVISION / 'backpack_before.json'
    if not before.exists():
        shutil.copy2(ROOT / 'backpack_fitted.json', before)
    data = read(ROOT / 'backpack_fitted.json')
    if data.get('shoulder_fit') == 'continuous_clothed_ribbons_20261003':
        data = read(before)
    source = read(ROOT / 'backpack.json')
    target = read(INPUT / 'Jason.json')
    v = np.asarray(source['positions'])
    t = np.asarray(source['triangles'], dtype=int)
    p = np.asarray(data['positions'])
    bones = {b['name']: b['index'] for b in target['bones']}
    mesh, garment_weights = make_envelope(target)
    centers = mesh.triangles_center
    tree = cKDTree(centers)

    # Weld only for island selection: keep the original seam-split vertex order
    # in the delivered asset so UV seams and the native material remain intact.
    welded, inv = np.unique(np.round(v, 4), axis=0, return_inverse=True)
    forward_triangles = t[np.all(v[t, 1] < -1., axis=1)]
    a = inv[forward_triangles]
    edges = np.vstack([a[:, [0, 1]], a[:, [1, 2]], a[:, [2, 0]]])
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                       shape=(len(welded), len(welded)))
    _, labels = connected_components(graph, directed=False)
    labels = labels[inv]
    used = np.unique(forward_triangles)
    shoulder_islands = sorted(np.unique(labels[used]),
                              key=lambda k: -(labels[used] == k).sum())[:2]
    recipes = []
    for island in shoulder_islands:
        indices = used[labels[used] == island]
        native = v[indices]
        side = -np.sign(np.median(native[:, 0]))
        # Angle along the original curved strap supplies a continuous material
        # coordinate, including duplicated vertices on UV boundaries.
        theta = np.arctan2(4. - native[:, 1], native[:, 2] + 15.)
        radial = np.hypot(4. - native[:, 1], native[:, 2] + 15.)
        grid = np.linspace(theta.min(), theta.max(), 181)
        x_mid, x_half, r_mid, r_half = [], [], [], []
        for angle in grid:
            near = np.argsort(np.abs(theta - angle))[:70]
            xl, xh = np.quantile(native[near, 0], [.035, .965])
            rl, rh = np.quantile(radial[near], [.12, .88])
            x_mid.append((xl + xh) / 2.)
            x_half.append(max((xh - xl) / 2., 1.))
            r_mid.append((rl + rh) / 2.)
            r_half.append(max((rh - rl) / 2., .16))
        x_mid, x_half, r_mid, r_half = [gaussian_filter1d(a, 4.)
                                       for a in [x_mid, x_half, r_mid, r_half]]
        across = (native[:, 0] - np.interp(theta, grid, x_mid)) / np.interp(theta, grid, x_half)
        across = np.clip(across, -1.06, 1.06)
        depth = (radial - np.interp(theta, grid, r_mid)) / np.interp(theta, grid, r_half)
        depth = np.clip(depth, -1., 1.) * .24
        s = (theta - grid[0]) / (grid[-1] - grid[0])
        # A padded shoulder/chest section narrows into the lower return webbing.
        # Both ends terminate on the original bag's front attachment surface.
        controls = np.asarray([
            [9.0, -10.4, 144.0], [12.3, -7.0, 146.5],
            [13.2, -1.0, 146.9], [13.0, 5.0, 143.4],
            [12.0, 10.1, 137.0], [11.5, 12.2, 128.0],
            [11.0, 11.5, 117.0], [12.2, 9.2, 109.0],
            [15.5, 4.5, 105.0], [17.0, -3.0, 103.5],
            [15.0, -10.8, 103.0]])
        controls[:, 0] *= side
        distances = np.r_[0., np.cumsum(np.linalg.norm(np.diff(controls, axis=0), axis=1))]
        distances /= distances[-1]
        curve = CubicSpline(distances, controls, axis=0, bc_type='natural')
        stations = np.linspace(0., 1., 241)
        path = curve(stations)
        tangent = unit(curve(stations, 1))
        outward = unit(np.column_stack([path[:, 0] * .3, path[:, 1] - 1.,
                                        np.maximum(path[:, 2] - 137., 0.) * 1.7]))
        width_axis = unit(np.cross(outward, tangent))
        # Keep the native +X texture direction mapped continuously to world -X.
        if width_axis[0, 0] > 0:
            width_axis *= -1
        for i in range(1, len(width_axis)):
            if np.dot(width_axis[i], width_axis[i - 1]) < 0:
                width_axis[i] *= -1
        normal = unit(np.cross(tangent, width_axis))
        if np.mean(np.einsum('ij,ij->i', normal, outward)) < 0:
            normal *= -1
        width = np.interp(stations, [0., .15, .52, .68, .78, 1.],
                          [4.2, 4.5, 4.3, 3.9, 2.3, 2.3])
        # Fit entire ribbon sections. Their width and physical thickness are
        # preserved; the most protruding shirt fold determines the clearance.
        for _ in range(2):
            samples = path[:, None, :] + width_axis[:, None, :] * width[:, None, None] * np.linspace(-.55, .55, 7)[None, :, None]
            origins = (samples + normal[:, None, :] * 16.).reshape(-1, 3)
            dirs = np.repeat(-normal, 7, axis=0)
            hit, ray, _ = mesh.ray.intersects_location(origins, dirs, multiple_hits=False)
            shifts = np.zeros(len(origins))
            dist = np.einsum('ij,ij->i', origins[ray] - hit, -dirs[ray])
            shifts[ray] = np.maximum(0., 16. + .85 - dist)
            lift = shifts.reshape(-1, 7).max(axis=1)
            lift = np.maximum(lift, gaussian_filter1d(lift, 3.))
            # Keep each sewn attachment rigid with the bag, blend in smoothly.
            attachment = smoothstep(stations / .08) * smoothstep((1. - stations) / .09)
            path += normal * (lift * attachment)[:, None]

        # Smooth section weights from the actual garment envelope; vertices on
        # both sides of each narrow section share them, avoiding saw-tooth skinning.
        _, nearest = tree.query(path, k=16)
        tris = mesh.triangles[nearest].reshape(-1, 3, 3)
        closest = trimesh.triangles.closest_point(tris, np.repeat(path, 16, axis=0)).reshape(-1, 16, 3)
        chosen = np.argmin(np.linalg.norm(closest - path[:, None], axis=2), axis=1)
        faces = mesh.faces[nearest[np.arange(len(path)), chosen]]
        contact = closest[np.arange(len(path)), chosen]
        bary = trimesh.triangles.points_to_barycentric(mesh.vertices[faces], contact)
        dense = (garment_weights[faces] * bary[:, :, None]).sum(axis=1)
        dense = gaussian_filter1d(dense, 4., axis=0)
        pin = 1. - smoothstep(stations / .14) * smoothstep((1. - stations) / .16)
        dense *= (1. - pin)[:, None]
        dense[:, bones['spine_03']] += pin
        dense /= dense.sum(axis=1)[:, None]
        sample_path = np.column_stack([np.interp(s, stations, path[:, j]) for j in range(3)])
        sample_width = unit(np.column_stack([np.interp(s, stations, width_axis[:, j]) for j in range(3)]))
        sample_normal = unit(np.column_stack([np.interp(s, stations, normal[:, j]) for j in range(3)]))
        fitted = sample_path + sample_width * (across * np.interp(s, stations, width) / 2.)[:, None] + sample_normal * depth[:, None]
        seam_blend = smoothstep((-native[:, 1] - 1.) / 3.)
        p[indices] = p[indices] * (1. - seam_blend)[:, None] + fitted * seam_blend[:, None]
        for local, vi in enumerate(indices):
            row = np.array([np.interp(s[local], stations, dense[:, b]) for b in range(dense.shape[1])]) * seam_blend[local]
            for bone, weight in data['weights'][vi]:
                row[bone] += weight * (1. - seam_blend[local])
            order = np.argsort(row)[-8:][::-1]
            order = order[row[order] > 1e-6]
            data['weights'][vi] = [[int(b), float(row[b] / row[order].sum())] for b in order]
        recipes.append({'side': int(side), 'vertices': len(indices), 'path': path.tolist(),
                        'width_cm': width.tolist(), 'clearance_cm': .61,
                        'thickness_cm': .48, 'lower_attachment': controls[-1].tolist()})
    data['positions'] = p.tolist()
    data['shoulder_fit'] = 'continuous_clothed_ribbons_20261003'
    (ROOT / 'backpack_fitted.json').write_text(json.dumps(data, separators=(',', ':')))
    (REVISION / 'recipe.json').write_text(json.dumps({'straps': recipes, 'runtime_tested': False}, indent=2))
    print('JASON_SHOULDER_RIBBONS_AUTHORED', sum(r['vertices'] for r in recipes), flush=True)


if __name__ == '__main__':
    refit()
