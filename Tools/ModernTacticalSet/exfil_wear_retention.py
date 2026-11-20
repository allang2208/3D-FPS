"""Dress the relaxed helmet retention assembly onto each character's jaw in Blender."""
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1.e-12)


def projection(points, centers):
    """Arc coordinates on the nearest ribbon segment, including rolled edges."""
    segments = np.diff(centers, axis=0)
    delta = points[:, None, :] - centers[:-1]
    t = np.clip((delta * segments).sum(2) / (segments * segments).sum(1), 0, 1)
    distance = np.linalg.norm(delta - t[:, :, None] * segments, axis=2)
    i = distance.argmin(1)
    return i + t[np.arange(len(points)), i]


def fit(data, parts, head, triangles, bone):
    face = BVHTree.FromPolygons(head.tolist(), triangles, all_triangles=True)
    reference = np.asarray(bone['position']) + [0, 2, 3]
    p = np.asarray(data['positions'])
    f = np.asarray(data['triangles'])
    fitted = p.copy()
    blocks = {}
    start = 0
    for name, count in parts.items():
        blocks[name] = f[start:start + count]
        start += count
    if start != len(f):
        raise ValueError('Retention part map must correspond to this game mesh')

    def samples(indices):
        corners = p[indices]
        return np.vstack((p[np.unique(indices)], corners.mean(1),
                          ((corners + np.roll(corners, 1, axis=1)) * .5).reshape(-1, 3)))

    def required(points, direction):
        # Fit the entire strap width to the actual facial surface, including the
        # jaw underside. Distances are in centimetres.
        result = np.zeros(len(points))
        axis = Vector(direction)
        for i, pt in enumerate(points):
            hit, _, _, depth = face.ray_cast(Vector(pt) + axis * 30, -axis, 36)
            if hit is not None:
                result[i] = max(0., 30.12 - depth)
        return result

    junctions = {}
    for side in ('R', 'L'):
        group = np.vstack([faces for k, faces in blocks.items() if k.startswith('Chin_Junction_' + side)])
        ids = np.unique(group)
        axis = unit(p[ids].mean(0) - reference)
        shift = axis * required(samples(group), axis).max()
        junctions[side] = shift
        fitted[ids] += shift  # release levers, pins and socket stay rigid

    names = ['Fore_Yoke_R', 'Fore_Yoke_L', 'Rear_Yoke_R', 'Rear_Yoke_L', 'Chin_Sling_Woven_Base']
    for name in names:
        sling = name == 'Chin_Sling_Woven_Base'
        related = [k for k in blocks if k.startswith(name) or
                   (sling and k.startswith(('Chin_Cup_', 'Chin_Reinforcement_')))]
        group = np.vstack([blocks[k] for k in related])
        rings = p[np.unique(blocks[name])].reshape(-1, 8, 3)
        centers = rings.mean(1)
        coords = np.arange(len(centers))
        surface = samples(group)
        # Include adjoining panels and trim when fitting each cross-section.
        ring_idx = np.rint(projection(surface, centers)).astype(int)
        directions = unit(centers - reference)
        amounts = np.array([required(surface[ring_idx == i], a).max(initial=0.)
                            for i, a in enumerate(directions)])
        smoothed = np.convolve(np.pad(amounts, 2, mode='edge'), [.1, .2, .4, .2, .1], 'valid')
        offsets = directions * np.maximum(amounts, smoothed)[:, None]
        # Ease the shared connector displacement into the webbing.
        ends = [(0, 'R'), (-1, 'L')] if sling else [(-1, name[-1])]
        for end, side in ends:
            dist = np.linalg.norm(centers - centers[end], axis=1)
            blend = np.clip(1. - dist / 1.5, 0, 1)
            blend = (blend * blend * (3 - 2 * blend))[:, None]
            offsets = offsets * (1 - blend) + junctions[side] * blend
        for k in related:
            ids = np.unique(blocks[k])
            arc = projection(p[ids], centers)
            if k == name:
                arc = np.repeat(coords, 8)
            elif any(tag in k for tag in ('_LadderLock', '_ClampBar', '_ClampRib_')):
                # All pieces of a slider share its location along the ribbon.
                anchor = p[np.unique(blocks[name + '_ClampBar'])].mean(0)
                arc = np.full(len(ids), projection(anchor[None], centers)[0])
            fitted[ids] += np.column_stack([np.interp(arc, coords, axis) for axis in offsets.T])

    # Rotate the original split normals with their triangle, preserving seams.
    def basis(points):
        edges = np.diff(points, axis=1)
        u = unit(edges[:, 0])
        w = unit(np.cross(u, edges[:, 1]))
        return np.stack((u, np.cross(w, u), w), axis=1)
    mask = np.any(abs(p[f] - fitted[f]) > 1.e-9, axis=(1, 2))
    normals = np.asarray(data['normals'])
    rot = basis(p[f[mask]]).transpose(0, 2, 1) @ basis(fitted[f[mask]])
    normals[mask] = unit(normals[mask] @ rot)
    data['positions'] = fitted.tolist()
    data['normals'] = normals.tolist()


def main():
    from exfil_reference_assembly import OUT, SET, read, save_json
    for rig in ('Jason', 'Kaitlin'):
        src = SET / 'HelmetHairFitR1/Inputs'
        native = read(src / f'{rig}_Head.json')
        h = native['bones']['head']
        b = read(src / f'{rig}_Body.json')['bones']['head']
        inv = np.linalg.inv(b['axes'])
        head = (np.asarray(native['positions']) - h['position']) @ np.linalg.inv(h['axes']) @ b['axes'] + b['position']
        folder = OUT / 'Authored'
        data = read(folder / f'helmet_{rig}_world.json')
        parts = read(folder / f'parts-{rig}-GAME.json')['parts']
        fit(data, parts, head, native['triangles'], b)
        data['positions'] = ((np.asarray(data['positions']) - b['position']) @ inv).tolist()
        data['normals'] = unit(np.asarray(data['normals']) @ np.asarray(b['axes']).T).tolist()
        data['attachment_frame'] = b
        save_json(folder / f'helmet_{rig}_wear.json', data)
        print('Retention fitted:', rig, flush=True)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
