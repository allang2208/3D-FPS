"""Build a tetrahedral embedding for the unchanged M14 surface (no simulation/test)."""
from pathlib import Path
import itertools, json, hashlib, urllib.request
import numpy as np
from scipy.ndimage import binary_fill_holes

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004'
OUT = ROOT/'ProductionV17'
for folder in ('Exports', 'Records', 'Authoring'):
    (OUT/folder).mkdir(parents=True, exist_ok=True)

source = np.load(ROOT/'ProductionV11/Records/hardware_source.npz')
p = source['p'].astype(np.float64)
binding = np.load(ROOT/'ProductionV13/Records/hardware_binding.npz')
owner, blend = binding['owner'], binding['blend']
weld = np.load(ROOT/'ProductionV11/Records/hardware_components.npz')['weld']
_, representative, inverse = np.unique(weld, return_index=True, return_inverse=True)
points = p[representative]

# Freudenthal tetrahedra give positive barycentric weights, including every
# surface point, without an extrapolated nearest-bone skin or new display faces.
spacing = .24
origin = np.floor(p.min(0)/spacing)*spacing - .012
q = (points-origin)/spacing
cells = np.floor(q).astype(np.int32)
shape = tuple(cells.max(0)+1)
occupied = np.zeros(shape, dtype=bool)
occupied[tuple(cells.T)] = True
occupied = binary_fill_holes(occupied)
occupied_cells = np.argwhere(occupied)
offsets = np.array(list(itertools.product((0, 1), repeat=3)), dtype=np.int32)
grid_nodes = np.unique((occupied_cells[:, None, :]+offsets).reshape(-1, 3), axis=0)
lookup = {tuple(value): i for i, value in enumerate(grid_nodes)}
nodes = (origin+grid_nodes*spacing).tolist()
tetra = []
for cell in occupied_cells:
    for axes in itertools.permutations(range(3)):
        corners = np.zeros((4, 3), np.int32)
        for step, axis in enumerate(axes):
            corners[step+1] = corners[step]
            corners[step+1, axis] = 1
        ids = [lookup[tuple(cell+corner)] for corner in corners]
        v = np.array([nodes[i] for i in ids])
        if np.linalg.det((v[1:]-v[0]).T) < 0:
            ids[1], ids[2] = ids[2], ids[1]
        tetra.append(ids)

fraction = q-cells
axes = np.argsort(-fraction, axis=1, kind='stable')
sorted_fraction = np.take_along_axis(fraction, axes, axis=1)
weights = np.column_stack((1-sorted_fraction[:, 0],
                          sorted_fraction[:, 0]-sorted_fraction[:, 1],
                          sorted_fraction[:, 1]-sorted_fraction[:, 2], sorted_fraction[:, 2]))
corners = np.zeros((len(points), 4, 3), np.int32)
rows = np.arange(len(points))
for step in range(3):
    corners[:, step+1] = corners[:, step]
    corners[rows, step+1, axes[:, step]] = 1
node_ids = np.array([[lookup[tuple(cell+c)] for c in cs]
                     for cell, cs in zip(cells, corners)], dtype=np.int32)

# Metal patches have separate rigid frames, retaining the V13 feathered tissue
# attachment and welded seam mapping. The simulation points enclose each patch.
hardware = []
hardware_index = np.full(len(p), -1, np.int32)
for cluster, cid in enumerate(binding['major']):
    solid = np.flatnonzero((owner == cid) & (blend >= .999999))
    region = p[solid]
    center = region.mean(0)
    _, _, basis = np.linalg.svd(region-center, full_matrices=False)
    if np.linalg.det(basis) < 0:
        basis[-1] *= -1
    extent = np.maximum(np.max(np.abs((region-center)@basis.T), axis=0), .025)
    # Symmetric four-point frame; hardware rendering uses only its rigid fit.
    local = np.array(((1,1,1),(1,-1,-1),(-1,1,-1),(-1,-1,1)))*extent
    frame_points = center+local@basis
    start = len(nodes)
    nodes.extend(frame_points.tolist())
    anchor = node_ids[np.argmin(np.sum((points-center)**2, axis=1))].tolist()
    hardware.append({'nodes': list(range(start, start+4)), 'center': center.tolist(),
                     'anchors': anchor, 'source_region': int(cid),
                     'radius': float(np.max(np.linalg.norm(region-center, axis=1)))})
    hardware_index[owner == cid] = cluster

# Welding before export gives all coincident material-cut copies one binding.
records = np.column_stack((points, node_ids, weights,
                          hardware_index[representative], blend[representative])).astype('<f4')
with (OUT/'Exports/embedding.bin').open('wb') as stream:
    stream.write(np.array([len(records), records.shape[1]], dtype='<i4').tobytes())
    stream.write(records.tobytes())
data = {'spacing_m': spacing, 'nodes': nodes, 'soft_node_count': len(grid_nodes),
        'tetrahedra': tetra, 'hardware': hardware, 'source': 'ProductionV15',
        'display_faces_removed': 0, 'embedding': 'positive tetrahedral barycentric weights'}
(OUT/'Exports/cage.json').write_text(json.dumps(data, separators=(',', ':'))+'\n', encoding='utf8')
# Editable cage geometry alongside JSON; tetrahedra remain in JSON for authoring.
with (OUT/'Authoring/M14_SoftProxy_v17.obj').open('w', encoding='utf8') as stream:
    for x,y,z in nodes:
        stream.write(f'v {x:.7f} {y:.7f} {z:.7f}\n')
    faces = {}
    for a,b,c,d in tetra:
        for face in ((a,c,b),(a,b,d),(a,d,c),(b,c,d)):
            key = tuple(sorted(face))
            faces[key] = None if key in faces else face
    for face in faces.values():
        if face:
            stream.write('f '+' '.join(str(i+1) for i in face)+'\n')

vendor = PROJECT/'Source/ThirdParty/PositionBasedDynamics'
vendor.mkdir(parents=True, exist_ok=True)
base = 'https://raw.githubusercontent.com/InteractiveComputerGraphics/PositionBasedDynamics/master/'
upstream = {}
for name in ('LICENSE', 'PositionBasedDynamics/XPBD.cpp'):
    content = urllib.request.urlopen(base+name, timeout=60).read()
    target = vendor/('LICENSE' if name == 'LICENSE' else 'XPBD.cpp.upstream.txt')
    target.write_bytes(content)
    upstream[name] = {'url': base+name, 'sha256': hashlib.sha256(content).hexdigest()}
(vendor/'provenance.json').write_text(json.dumps({'retrieved': '2026-10-05',
    'repository': 'https://github.com/InteractiveComputerGraphics/PositionBasedDynamics',
    'files': upstream, 'integration': 'Distance and volume XPBD kernels adapted to UE FVector in M14XPBDConstraints.h; explicit 1/6 volume gradients.'}, indent=2)+'\n', encoding='utf8')
(OUT/'Records/authoring.json').write_text(json.dumps({'complete': True,
    'soft_nodes': len(grid_nodes), 'hardware_nodes': len(nodes)-len(grid_nodes),
    'tetrahedra': len(tetra), 'hardware_regions': len(hardware), 'surface_rows': len(records),
    'source_vertices': len(p), 'source_triangles': len(source['f']),
    'geometry_removed': 0, 'tested': False, 'rendered': False}, indent=2)+'\n', encoding='utf8')
print('M14_V17_CAGE_AUTHORED', len(nodes), len(tetra), len(records), flush=True)
