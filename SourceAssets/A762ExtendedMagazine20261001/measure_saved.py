"""Scoped seam/UV measurements for the requested magazine revision."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

folder = Path(__file__).parent
stage = sys.argv[1] if len(sys.argv) > 1 else 'SavedGeometry'
file = folder / stage / 'A762_ext_mag.bin'
with file.open('rb') as stream:
    meta = json.loads(stream.readline())
    nv, nt = meta['vertices'], meta['triangles']
    positions = np.fromfile(stream, np.float32, nv * 3).reshape(nv, 3)
    triangles = np.fromfile(stream, np.int32, nt * 3).reshape(nt, 3)
    materials = np.fromfile(stream, np.int32, nt)
    uv = np.fromfile(stream, np.float32, nt * 6).reshape(nt, 3, 2)
    normals = np.fromfile(stream, np.float32, nt * 9).reshape(nt, 3, 3)

# Weld only numerically identical positions; source dimensions are UE cm.
_, inverse = np.unique(np.round(positions, 6), axis=0, return_inverse=True)
indices = inverse[triangles]
edges = np.sort(np.concatenate((indices[:, [0, 1]], indices[:, [1, 2]], indices[:, [2, 0]])), axis=1)
_, counts = np.unique(edges, axis=0, return_counts=True)
points = positions[triangles].astype(np.float64)
areas = np.linalg.norm(np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]), axis=1) * .5
a, b = uv[:, 1].astype(np.float64) - uv[:, 0], uv[:, 2].astype(np.float64) - uv[:, 0]
uv_areas = np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) * .5
data = {
    'asset': meta['path'], 'asset_sha256': json.loads((file.parent / 'current.json').read_text())['sha256'],
    'fbx_sha256': hashlib.sha256((folder / 'Exports/SM_A762_ext_mag_Continuous07.fbx').read_bytes()).hexdigest(),
    'vertices': nv, 'triangles': nt,
    'authored_triangles': json.loads((folder / 'authoring.json').read_text())['triangles'],
    'boundary_edges_at_1e_minus_6_cm': int(np.sum(counts == 1)),
    'nonmanifold_edges_at_1e_minus_6_cm': int(np.sum(counts > 2)),
    'zero_area_triangles': int(np.sum(areas == 0)),
    'collapsed_uv_triangles': int(np.sum(uv_areas == 0)),
    'finite_normals': bool(np.isfinite(normals).all()),
    'bounds_cm': [positions.min(axis=0).tolist(), positions.max(axis=0).tolist()],
    'triangles_by_material': {name: int(np.sum(materials == i)) for i, name in enumerate(meta['slots'])},
    'material_bindings': dict(zip(meta['slots'], meta['materials'])),
    'runtime_tested': False,
}
(file.parent / 'seam_measurements.json').write_text(json.dumps(data, indent=2))
print(json.dumps(data, indent=2))
