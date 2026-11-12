"""Build the female collar on the actual independent head, with a shared skin bind.

Only the neck component is replaced; sleeves, waist pairs and their UVs stay in
the source DynamicMesh. All lengths are derived from the female neck dimensions.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import trimesh

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/ST6FemaleCollar20261108')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def unit(values):
    return values / np.maximum(np.linalg.norm(values, axis=-1, keepdims=True), 1e-12)


def normals(points, faces):
    result = np.zeros_like(points)
    # UE source triangles wind clockwise relative to outward normals.
    area = -np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    for i in range(3):
        np.add.at(result, faces[:, i], area)
    return unit(result)


def mix(rows, fractions):
    result = {}
    for row, fraction in zip(rows, fractions):
        for bone, weight in row.items():
            result[bone] = result.get(bone, 0.) + weight * float(fraction)
    result = dict(sorted(result.items(), key=lambda v: -v[1])[:8])
    total = sum(result.values())
    return {bone: weight / total for bone, weight in result.items() if weight > 1e-8}


class Surface:
    def __init__(self, data, faces, bone_names):
        self.points = np.asarray(data['positions'], float)
        self.faces = np.asarray(faces, int)
        self.triangles = self.points[self.faces]
        self.tree = cKDTree(self.triangles.mean(axis=1))
        self.normals = normals(self.points, self.faces)
        mapped = []
        for bone in data['bones']:
            while bone['name'] not in bone_names:
                bone = data['bones'][bone['parent']]
            mapped.append(bone['name'])
        self.weights = [mix([{mapped[b]: 1.} for b, _ in row], [w for _, w in row]) for row in data['weights']]

    def project(self, query):
        query = np.atleast_2d(query)
        _, candidates = self.tree.query(query, k=min(24, len(self.faces)))
        triangles = self.triangles[candidates]
        closest = trimesh.triangles.closest_point(triangles.reshape(-1, 3, 3),
            np.repeat(query, candidates.shape[1], axis=0)).reshape(len(query), -1, 3)
        choice = np.argmin(np.linalg.norm(closest - query[:, None, :], axis=2), axis=1)
        index = candidates[np.arange(len(query)), choice]
        position = closest[np.arange(len(query)), choice]
        bary = trimesh.triangles.points_to_barycentric(self.triangles[index], position)
        n = unit((self.normals[self.faces[index]] * bary[:, :, None]).sum(axis=1))
        weights = [mix([self.weights[v] for v in self.faces[f]], b) for f, b in zip(index, bary)]
        return position, n, weights


def main():
    manifest = read(WORK / 'manifest.json')
    head, body = [read(WORK / 'Inputs' / name) for name in ('head.json', 'body.json')]
    bones = {b['name']: b for b in body['bones']}
    neck_length = bones['neck_02']['position'][2] - bones['neck_01']['position'][2]
    # Keep the current female opening height, using her existing garment only as
    # the style reference. The replacement surface comes from her native head.
    baseline = read(WORK / 'Inputs' / manifest['meshes'][1]['file'])
    top = max(p[2] for p in baseline['positions'])
    hp = np.asarray(head['positions'], float)
    hf = np.asarray(head['triangles'], int)
    # Below this neckline the independent head contains only the neck/shoulder
    # skin; eyes, teeth and lashes are above the clipping plane.
    head_faces = hf[hp[hf, 2].min(axis=1) <= top + neck_length]
    surface = Surface(head, head_faces, bones)
    bp = np.asarray(body['positions'], float)
    bf = np.asarray(body['triangles'], int)
    body_faces = bf[bp[bf, 2].min(axis=1) > bones['spine_05']['position'][2] - neck_length]
    body_surface = Surface(body, body_faces, bones)
    points, weights, faces, cache = [], [], [], {}
    for face in head_faces:
        if hp[face, 2].min() >= top:
            continue
        poly = []
        for a, b in zip(face, np.roll(face, -1)):
            if hp[a, 2] <= top:
                poly.append((hp[a], surface.weights[a]))
            if (hp[a, 2] <= top) != (hp[b, 2] <= top):
                t = (top - hp[a, 2]) / (hp[b, 2] - hp[a, 2])
                poly.append((hp[a] + (hp[b] - hp[a]) * t,
                             mix([surface.weights[a], surface.weights[b]], [1-t, t])))
        ids = []
        for p, w in poly:
            key = tuple(np.round(p, 6))
            if key not in cache:
                cache[key] = len(points)
                points.append(p.tolist())
                weights.append(w)
            ids.append(cache[key])
        for i in range(1, len(ids)-1):
            faces.append([ids[0], ids[i], ids[i+1]])
    points = np.asarray(points, float)
    faces = np.asarray(faces, int)
    edge_count = Counter(tuple(sorted((int(a), int(b)))) for f in faces for a, b in zip(f, np.roll(f, -1)))
    boundary = [e for e, count in edge_count.items() if count == 1]
    top_edges = [e for e in boundary if min(points[list(e), 2]) > top - 1e-5]
    bottom_edges = [e for e in boundary if e not in top_edges]
    top_ids = sorted({v for e in top_edges for v in e})
    bottom_ids = sorted({v for e in bottom_edges for v in e})
    distance, _ = cKDTree(points[bottom_ids]).query(points)
    blend = np.clip(distance / (neck_length * .35), 0, 1)
    blend = blend * blend * (3 - 2 * blend)
    _, ns, _ = surface.project(points)
    _, _, body_weights = body_surface.project(points)
    weights = [mix([bw, hw], [1-t, t]) for bw, hw, t in zip(body_weights, weights, blend)]
    # The face points forward along +Y on this native female mesh. Reserve a
    # little more room at the throat while keeping the chest join close.
    front = np.clip(ns[:, 1], 0, 1)
    clearance = neck_length * (.038 + .014 * blend + .014 * front * blend)
    out = (points + ns * clearance[:, None]).tolist()
    out_weights = list(weights)
    out_faces = faces.tolist()
    directed = {tuple(sorted((int(a), int(b)))): (int(a), int(b)) for f in faces for a, b in zip(f, np.roll(f, -1))}

    rings = [{v: v for v in top_ids}]
    for down, gap in ((.012, .042), (.045, .030), (.150, .027)):
        query = points[top_ids].copy()
        query[:, 2] -= neck_length * down
        q, n, w = surface.project(query)
        ring = {}
        for index, vertex in enumerate(top_ids):
            ring[vertex] = len(out)
            out.append((q[index] + n[index] * neck_length * gap).tolist())
            # Outer lip and inner return share the opening's bone weights.
            out_weights.append(dict(weights[vertex]))
        rings.append(ring)
    for e in top_edges:
        a, b = directed[e]
        for ra, rb in zip(rings, rings[1:]):
            out_faces.extend([[ra[b], ra[a], rb[a]], [ra[b], rb[a], rb[b]]])

    # Extend the lower edge over the native cloth material by a short strip.
    # Sample the true body again so this underlap follows the chest/shoulder.
    query = points[bottom_ids].copy()
    query[:, 2] -= neck_length * .13
    q, n, w = body_surface.project(query)
    underlap = {}
    for index, vertex in enumerate(bottom_ids):
        underlap[vertex] = len(out)
        out.append((q[index] + n[index] * neck_length * .027).tolist())
        out_weights.append(w[index])
    for e in bottom_edges:
        a, b = directed[e]
        out_faces.extend([[b, a, underlap[a]], [b, underlap[a], underlap[b]]])
    p, f = np.asarray(out), np.asarray(out_faces, int)
    nn = normals(p, f)
    # Use the existing rest-space fabric material; UVs remain well-defined for
    # any later cloth material, with the seam split on the back of the neck.
    uv = []
    for face in f:
        angle = np.arctan2(p[face, 0], p[face, 1]) / (2*np.pi) + .5
        if np.ptp(angle) > .5:
            angle[angle < .5] += 1
        uv.append([[float(a), float((top-p[v, 2]) / 18)] for a, v in zip(angle, face)])
    patch = dict(positions=out, triangles=out_faces, weights=out_weights,
        normals=[[nn[v].tolist() for v in face] for face in f], uv=uv,
        top_cm=top, neck_length_cm=neck_length, clearance_cm=[float(clearance.min()), float(clearance.max())],
        inner_return_cm=neck_length*.15, chest_underlap_cm=neck_length*.13,
        head_source=head['source'], body_source=body['source'], runtime_tested=False)
    (WORK / 'collar.json').write_text(json.dumps(patch, separators=(',', ':')), encoding='utf-8')
    for row in manifest['meshes']:
        d = read(WORK / 'Inputs' / row['file'])
        collar_slot = next(i for i, m in enumerate(d['materials']) if m['slot'] == 'ST6NeckAndHemFabric')
        row['remove_triangles'] = [i for i, face in enumerate(d['triangles'])
            if d['triangle_materials'][i] == collar_slot and min(d['positions'][v][2] for v in face) > 120]
        row['collar_slot'] = collar_slot
        row['source_sha256'] = d['source_sha256']
    manifest['collar_sha256'] = hashlib.sha256((WORK / 'collar.json').read_bytes()).hexdigest()
    manifest['authored'] = True
    (WORK / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('ST6_FEMALE_COLLAR_AUTHORED', len(out), 'vertices;', len(out_faces), 'triangles;', len(manifest['meshes']), 'variants')


if __name__ == '__main__':
    main()
