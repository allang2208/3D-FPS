"""Make six open, low-density midsurfaces for the retained tissue panels."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree, Delaunay

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'Authoring'
source = np.load(OUT/'source_mesh.npz')
regions = np.load(OUT/'source_regions.npz')['face_labels']
guide = json.loads((OUT/'region_authoring.json').read_text())
raw = source['positions'].astype(np.float64)
points = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1]-guide['ground_source_y']]*guide['scale_to_meters']
triangles = source['indices'].reshape(-1, 3)
records = []
for panel in range(1, 7):
    ids = np.unique(triangles[regions == panel].ravel())
    pts = points[ids]
    # Parameterise the thin, broadly vertical panel by its actual lateral/up
    # silhouette. Average paired inner/outer samples into one simulation sheet.
    step = .045
    planar = pts[:, [0, 2]]
    origin = planar.min(axis=0)
    cell = np.rint((planar-origin)/step).astype(np.int32)
    bins, inv = np.unique(cell, axis=0, return_inverse=True)
    accum = np.zeros((len(bins), 3))
    np.add.at(accum, inv, pts)
    cnt = np.bincount(inv)
    proxy = accum/cnt[:, None]
    tri = Delaunay(proxy[:, [0, 2]]).simplices
    lengths = np.stack([np.linalg.norm(proxy[tri[:, i]]-proxy[tri[:, (i+1)%3]], axis=1) for i in range(3)])
    tri = tri[lengths.max(axis=0) < step*3.4]
    # Preserve only the sheet attached to its uppermost anchor; region seam
    # fragments remain in the high-detail surface, not as loose simulated debris.
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    edges = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(proxy), len(proxy))).tocsr()
    _, comp = connected_components(graph, directed=False)
    connected = comp == comp[int(np.argmax(proxy[:, 2]))]
    tri = tri[np.all(connected[tri], axis=1)]
    used = np.unique(tri.ravel())
    lookup = np.full(len(proxy), -1, dtype=np.int32); lookup[used] = np.arange(len(used))
    proxy = proxy[used]; tri = lookup[tri]
    if len(tri) < 10:
        raise RuntimeError('Insufficient continuous cloth surface for panel '+str(panel))
    top = float(np.quantile(proxy[:, 2], .98))
    # Fixed shoulder/back seam transitions smoothly into a tissue motion budget.
    drop = np.clip((top-proxy[:, 2]-.055)/.24, 0, 1)
    free = drop*drop*(3-2*drop)
    max_cm = (3.0 + 7.0*free)*free
    pin = 1-free
    np.savez_compressed(OUT/f'cloth_proxy_{panel:02d}.npz', positions=proxy.astype(np.float32),
                        triangles=tri.astype(np.int32), pin=pin.astype(np.float32),
                        max_distance_cm=max_cm.astype(np.float32))
    records.append({'id': f'{panel:02d}', 'vertices_cm': (proxy*100).tolist(),
                    'max_distance_cm': max_cm.tolist(), 'pin_weights': pin.tolist(),
                    'source_region': panel, 'vertex_count': len(proxy), 'triangle_count': len(tri),
                    'root_world_m': proxy[proxy[:, 2] >= top-.055].mean(axis=0).tolist(),
                    'tip_world_m': proxy[proxy[:, 2] <= np.quantile(proxy[:, 2], .08)].mean(axis=0).tolist()})
manifest = {'panels': records, 'collision_capsules': [], 'units': 'UE cm; Blender authoring metres',
            'method': 'Open single-layer regular midsurfaces from source panel silhouettes, with shoulder/back pin weights',
            'cross_panel_collision': 'Six assets use body collision; independent assets do not provide inter-panel collision',
            'tested': False}
(OUT/'cloth_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'panels': [{'id': r['id'], 'vertices': r['vertex_count'], 'triangles': r['triangle_count']} for r in records]}), flush=True)
