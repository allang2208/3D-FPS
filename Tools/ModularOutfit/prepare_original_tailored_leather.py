"""Map the accepted fingerless leather authoring fields onto full tactical gloves.

Only auxiliary authoring UVs change; silhouette, positions and weights are kept.
The first-person family retains its existing shared UV0. Body receives its own
bake because its old triplanar-only glove had a collapsed UV channel.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P, read, write
from tailored_fingerless_candidate import frame, unit, smooth

R = P/'SourceAssets/ModularOutfit20260927/OriginalLeatherV2'
FITTED = P/'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored'
canonical_bones = read(P/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources/M4.json')['bones']
anatomy = read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']


def rotation(bone):
    return unit(np.asarray(bone['axes'])).T


def prepare(name):
    d = read(FITTED/f'{name}.json')
    bones = canonical_bones if name == 'M4' else read(P/'SourceAssets/ModularOutfit20260924/NativeSkin/Body_source.json')['bones']
    positions = np.asarray(d['positions']); triangles = np.asarray(d['triangles'])
    normals = np.zeros_like(positions)
    for corner in range(3): np.add.at(normals, triangles[:, corner], np.asarray(d['normals'])[:, corner])
    normals = unit(normals)
    local = np.zeros_like(positions); back = np.zeros(len(positions))
    for side in ('l', 'r'):
        hand = 'hand_'+side
        transform = rotation(bones[hand])@rotation(canonical_bones[hand]).T
        native_anatomy = {side: {'dorsal': (transform@np.asarray(anatomy[side]['dorsal'])).tolist()}}
        basis, wrist = frame(bones, native_anatomy, side)
        digit_vectors = {digit['bone']: np.asarray(digit['dorsal']) for digit in anatomy[side]['digits']}
        for vi, weights in enumerate(d['weights']):
            if sum(w for n, w in weights.items() if n.endswith('_'+side)) <= .5: continue
            local[vi] = basis@(positions[vi]-wrist)
            amount = sum(w for n, w in weights.items() if n in digit_vectors)
            dorsal = transform@np.asarray(anatomy[side]['dorsal'])*max(0, 1-amount)
            for bone, weight in weights.items():
                if bone in digit_vectors:
                    transport = rotation(bones[bone])@rotation(canonical_bones[bone]).T
                    dorsal += transport@digit_vectors[bone]*weight
            back[vi] = smooth(-.10, .60, float(normals[vi]@unit(dorsal)))

    counts = Counter(tuple(sorted((int(f[k]), int(f[(k+1)%3])))) for f in triangles for k in range(3))
    edges = np.asarray(list(counts)); lengths = np.linalg.norm(positions[edges[:,0]]-positions[edges[:,1]], axis=1)
    graph = coo_matrix((np.r_[lengths,lengths], (np.r_[edges[:,0],edges[:,1]], np.r_[edges[:,1],edges[:,0]])), shape=(len(positions),len(positions))).tocsr()
    adj = defaultdict(list)
    for (a,b), count in counts.items():
        if count == 1: adj[a].append(b); adj[b].append(a)
    boundary = np.asarray(sorted(adj))
    distance = dijkstra(graph, indices=boundary, min_only=True, directed=False)
    arc = np.zeros(len(positions)); remaining = set(adj)
    while remaining:
        start = min(remaining); current = start; previous = -1; travelled = 0.
        while current in remaining:
            remaining.remove(current); arc[current] = travelled
            options = [n for n in adj[current] if n != previous]
            if not options: break
            nxt = options[0]; travelled += float(np.linalg.norm(positions[nxt]-positions[current]))
            previous, current = current, nxt
    _, near = cKDTree(positions[boundary]).query(positions)
    arc = arc[boundary[near]]
    original_uv = d['uv']
    metric = []
    # Same metric projection and 25 cm scan scale as the accepted fingerless author.
    for face in triangles:
        points = local[face]; cross = np.cross(points[1]-points[0], points[2]-points[0])
        axis = int(np.argmax(abs(cross))); keep = [a for a in range(3) if a != axis]
        coords = points[:,keep]/25.
        if cross[axis] < 0: coords[:,0] *= -1
        coords += np.asarray([axis*.173, axis*.293]); metric.append(coords.tolist())
    d.update(bones=bones, uv=metric,
             uv1=np.stack((1-back[triangles], distance[triangles]), axis=-1).tolist(),
             uv2=np.stack((arc[triangles], np.zeros_like(arc[triangles])), axis=-1).tolist(),
             uv3=np.stack(((local[triangles,0]+8)/16, (local[triangles,1]+5)/18), axis=-1).tolist(),
             target_uv=original_uv,
             contract='Full tactical glove; unchanged geometry and weights; accepted fingerless leather baked for this UV layout')
    write(R/'Authoring'/f'{name}.json', d)
    print('ORIGINAL_TAILORED_FIELDS_AUTHORED', name, flush=True)


if __name__ == '__main__':
    for profile in ('M4', 'Body'): prepare(profile)
    write(R/'material-source.json', dict(source_family='TailoredFingerlessV1',
          author='Tools/ModularOutfit/build_tailored_fingerless_candidate.py:authored_material',
          grain='same licensed 25 cm scan, palm strength .40 / back .58',
          roughness='same scan*.30+.34; contact polish -.10; specular .42',
          geometry_changed=False, runtime_tested=False))
