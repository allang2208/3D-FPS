"""Author per-mesh positive tetrahedral embeddings; no simulation or tests."""
from pathlib import Path
import itertools
import json
import numpy as np
from scipy.ndimage import binary_fill_holes, label
from scipy.spatial import cKDTree

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MonsterSoftCorpse20261005')
OFFSETS = np.array(list(itertools.product((0, 1), repeat=3)), dtype=np.int32)
PERMUTATIONS = list(itertools.permutations(range(3)))


def author(item):
    out = ROOT/item['key']
    with (out/'surface.bin').open('rb') as stream:
        count = int(np.fromfile(stream, dtype='<i4', count=1)[0])
        p = np.fromfile(stream, dtype='<f4').reshape(count, 3).astype(np.float64)
    # Identical positions across UV/material seams receive identical weights.
    points = np.unique(p, axis=0)
    spacing = max(float(np.ptp(points, axis=0).max())/16., .015)
    while True:
        origin = np.floor(points.min(0)/spacing)*spacing - spacing*.05
        q = (points-origin)/spacing
        cells = np.floor(q).astype(np.int32)
        occupied = np.zeros(tuple(cells.max(0)+1), dtype=bool)
        occupied[tuple(cells.T)] = True
        occupied = binary_fill_holes(occupied)
        # Separate teeth/eyes/attachments share the same local field. Join only
        # disconnected voxel islands by their shortest local bridge.
        components, number = label(occupied, structure=np.ones((3, 3, 3)))
        if number > 1:
            sizes = np.bincount(components.ravel()); sizes[0] = 0
            joined = np.argwhere(components == sizes.argmax())
            for component in np.argsort(-sizes)[1:]:
                if component == 0:
                    continue
                island = np.argwhere(components == component)
                distances, nearest = cKDTree(joined).query(island)
                index = distances.argmin()
                start, end = island[index], joined[nearest[index]]
                steps = int(np.abs(end-start).max())+1
                bridge = np.rint(np.linspace(start, end, steps)).astype(np.int32)
                occupied[tuple(bridge.T)] = True
                joined = np.concatenate((joined, island, bridge))
        full_cells = np.argwhere(occupied)
        grid = np.unique((full_cells[:, None, :]+OFFSETS).reshape(-1, 3), axis=0)
        if len(grid) <= 700:
            break
        spacing *= 1.08
    lookup = {tuple(v): i for i, v in enumerate(grid)}
    nodes = origin+grid*spacing
    tets = []
    for cell in full_cells:
        for axes in PERMUTATIONS:
            corner = np.zeros(3, dtype=np.int32)
            ids = [lookup[tuple(cell)]]
            for axis in axes:
                corner = corner.copy()
                corner[axis] += 1
                ids.append(lookup[tuple(cell+corner)])
            if np.linalg.det((nodes[ids[1:]]-nodes[ids[0]]).T) < 0:
                ids[1], ids[2] = ids[2], ids[1]
            tets.append(ids)
    fraction = q-cells
    axes = np.argsort(-fraction, axis=1, kind='stable')
    f = np.take_along_axis(fraction, axes, axis=1)
    weights = np.column_stack((1-f[:, 0], f[:, 0]-f[:, 1], f[:, 1]-f[:, 2], f[:, 2]))
    corners = np.zeros((len(points), 4, 3), np.int32)
    rows = np.arange(len(points))
    for step in range(3):
        corners[:, step+1] = corners[:, step]
        corners[rows, step+1, axes[:, step]] = 1
    node_ids = np.array([[lookup[tuple(cell+c)] for c in cs] for cell, cs in zip(cells, corners)], dtype=np.int32)
    records = np.column_stack((points, node_ids, weights, np.full(len(points), -1), np.zeros(len(points)))).astype('<f4')
    with (out/'embedding.bin').open('wb') as stream:
        np.array(records.shape, dtype='<i4').tofile(stream)
        records.tofile(stream)
    cage = dict(coordinates='mesh_m', spacing_m=spacing, nodes=nodes.tolist(),
                soft_node_count=len(nodes), tetrahedra=tets, hardware=[],
                source=item['source'], embedding='continuous positive tetrahedral field')
    (out/'cage.json').write_text(json.dumps(cage, separators=(',', ':'))+'\n', encoding='utf8')
    report = dict(complete=True, nodes=len(nodes), tetrahedra=len(tets), spacing_cm=spacing*100,
                  source_vertices=count, surface_rows=len(points), tested=False, rendered=False)
    (out/'authoring.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print('SOFT_CORPSE_AUTHORED', item['key'], len(nodes), len(tets), flush=True)


if __name__ == '__main__':
    for entry in json.loads((ROOT/'sources.json').read_text(encoding='utf8')):
        author(entry)
