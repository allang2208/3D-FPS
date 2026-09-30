"""Rebuild the remaining FP cotton sleeves in each active native bare-arm bind.

Reuse the Traversal repair's paired-shell construction, including its open
shoulder thickness ring. Never reuse the old torso-tethered shirt weights.
Run with background Blender; no preview, animation playback or rendering.
"""
import sys
import math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P = Path('D:/FPS3D/FPSGAME')
R = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'Tools/ModularOutfit'))
from garment_pipeline import read, write, digest


def surface_weights(skin, points, indices, hit):
    a, b, c = points[indices]
    v0, v1, v2 = b - a, c - a, np.asarray(hit) - a
    den = (v0 @ v0) * (v1 @ v1) - (v0 @ v1) ** 2
    if abs(den) < 1e-12:
        raise RuntimeError('Degenerate native arm triangle')
    v = ((v1 @ v1) * (v2 @ v0) - (v0 @ v1) * (v2 @ v1)) / den
    w = ((v0 @ v0) * (v2 @ v1) - (v0 @ v1) * (v2 @ v0)) / den
    bary = np.maximum([1 - v - w, v, w], 0)
    bary /= bary.sum()
    result = {}
    for vertex, blend in zip(indices, bary):
        for name, value in skin['weights'][vertex].items():
            result[name] = result.get(name, 0.) + float(blend * value)
    result = dict(sorted(((n, v) for n, v in result.items() if v > 1e-6), key=lambda x: -x[1])[:8])
    total = sum(result.values())
    return {n: v / total for n, v in result.items()}


def build(profile):
    folder = R / 'Before' / profile
    paths, skin = read(folder / 'paths.json'), read(folder / 'skin.json')
    sp, sf, sm = np.asarray(skin['positions']), np.asarray(skin['triangles']), np.asarray(skin['materials'])
    arm_mass = np.array([[sum(v for n, v in weights.items() if n.endswith('_' + side)
        and n.startswith(('clavicle', 'upperarm', 'lowerarm', 'hand')))
        for side in ('l', 'r')] for weights in skin['weights']])
    total_mass = arm_mass.sum(axis=0)
    sides = [s for i, s in enumerate(('l', 'r')) if total_mass[i] > total_mass.max() * .05]
    d = dict(profile=profile, binding_source=paths['skin'], bones=skin['bones'],
        positions=[], weights=[], triangles=[], uv=[], normals=[], triangle_materials=[],
        source_shirt=paths['shirt'], source_skin_sha256=paths['skin_sha256'])
    segments, rows, tau = 80, 24, math.tau
    for side in sides:
        side_index = ('l', 'r').index(side)
        a = np.array(d['bones']['upperarm_' + side]['position'])
        b = np.array(d['bones']['lowerarm_' + side]['position'])
        axis = (b - a) / np.linalg.norm(b - a)
        length = np.linalg.norm(b - a) * .55
        x = np.array([0., 1., 0.])
        x -= axis * np.dot(x, axis)
        if np.linalg.norm(x) < .01:
            x = np.array([1., 0., 0.]); x -= axis * np.dot(x, axis)
        x /= np.linalg.norm(x)
        y = np.cross(axis, x)
        face_mass = arm_mass[sf].sum(axis=1)
        faces = sf[(sm == 0) & (face_mass[:, side_index] > face_mass[:, 1 - side_index])]
        if not len(faces):
            raise RuntimeError('No native upper arm: ' + profile + '/' + side)
        tree = BVHTree.FromPolygons([Vector(p) for p in sp], faces.tolist(), all_triangles=True)
        stations = np.linspace(-1., length, rows)
        radii, weight_field = np.zeros((rows, segments)), {}
        for j, t in enumerate(stations):
            center = a + axis * t
            for i in range(segments):
                direction = x * math.cos(tau * i / segments) + y * math.sin(tau * i / segments)
                origin, travel, hits = center.copy(), 0., []
                for _ in range(6):
                    hit, normal, fi, distance = tree.ray_cast(Vector(origin), Vector(direction), 16 - travel)
                    if hit is None:
                        break
                    travel = float((np.array(hit) - center) @ direction)
                    triangle = sp[faces[fi]]
                    outward = -np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
                    if outward @ direction > 0:
                        hits.append((travel, hit, fi))
                    origin = np.array(hit) + direction * .002
                    travel += .002
                if hits:
                    radius, hit, fi = max(hits, key=lambda h: h[0])
                    radii[j, i] = radius
                    weight_field[j, i] = surface_weights(skin, sp, faces[fi], hit)
        # FP bare arms are open at the root. Extend a nearby complete section;
        # never fill the opening or reach across to a torso/opposite arm.
        for j in range(rows):
            for i in range(segments):
                if radii[j, i] > 0:
                    continue
                choices = [k for k in range(rows) if radii[k, i] > 0]
                if not choices:
                    raise RuntimeError('Missing native arm section: ' + profile + '/' + side)
                k = min(choices, key=lambda k: abs(k - j))
                radii[j, i], weight_field[j, i] = radii[k, i], weight_field[k, i]
        radii = np.maximum(radii, (np.roll(radii, 1, 1) + 2 * radii + np.roll(radii, -1, 1)) / 4)
        offset = len(d['positions'])
        for layer, clearance in enumerate((.85, .60)):
            for j, t in enumerate(stations):
                ease = .95 * max(0., 1. - max(0., t) / 6.) ** 2
                for i in range(segments):
                    direction = x * math.cos(tau * i / segments) + y * math.sin(tau * i / segments)
                    d['positions'].append((a + axis * t + direction * (radii[j, i] + clearance + ease)).tolist())
                    d['weights'].append(weight_field[j, i])

        def vertex(layer, j, i):
            return offset + layer * rows * segments + j * segments + i % segments

        def face(ids, coords, material, outward):
            p = np.array([d['positions'][i] for i in ids])
            if np.cross(p[1] - p[0], p[2] - p[0]) @ outward > 0:
                ids, coords = ids[::-1], coords[::-1]
            d['triangles'].append(ids); d['uv'].append(coords); d['triangle_materials'].append(material)

        for layer in (0, 1):
            for j in range(rows - 1):
                for i in range(segments):
                    ids = [vertex(layer, j, i), vertex(layer, j, i + 1), vertex(layer, j + 1, i + 1), vertex(layer, j + 1, i)]
                    u0, u1 = tau * 6 * i / segments / 25, tau * 6 * (i + 1) / segments / 25
                    coords = [[u0, stations[j] / 25], [u1, stations[j] / 25], [u1, stations[j + 1] / 25], [u0, stations[j + 1] / 25]]
                    outward = (x * math.cos(tau * (i + .5) / segments) + y * math.sin(tau * (i + .5) / segments)) * (1 if layer == 0 else -1)
                    for corners in ((0, 1, 2), (0, 2, 3)):
                        face([ids[k] for k in corners], [coords[k] for k in corners], 0 if layer == 0 else 2, outward)
        for j in (0, rows - 1):
            for i in range(segments):
                ids = [vertex(0, j, i), vertex(0, j, i + 1), vertex(1, j, i + 1), vertex(1, j, i)]
                coords = [[i / segments, 0], [(i + 1) / segments, 0], [(i + 1) / segments, .25 / 25], [i / segments, .25 / 25]]
                for corners in ((0, 1, 2), (0, 2, 3)):
                    face([ids[k] for k in corners], [coords[k] for k in corners], 1, axis * (-1 if j == 0 else 1))
    points, faces = np.array(d['positions']), np.array(d['triangles'])
    normals = np.zeros_like(points)
    cross = -np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    for corner in range(3):
        np.add.at(normals, faces[:, corner], cross)
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    d['normals'] = normals[faces].tolist()
    d['contract'] = 'Native V7 fitted charcoal short sleeves; paired shell weights; open shoulder and cuff thickness rings; no torso-tethered legacy geometry; existing cotton materials'
    write(R / 'Authored' / (profile + '.json'), d)
    print('CHARCOAL_FP_AUTHORED', profile, sides, len(d['triangles']), flush=True)


if __name__ == '__main__':
    for profile in read(R / 'before.json')['sources']:
        if profile != 'SVD':
            build(profile)
