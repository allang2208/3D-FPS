"""Requested closed-side diagnosis on every saved render LOD."""
import json
from pathlib import Path
import numpy as np
import trimesh

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BackpackHarnessRebuild20261020')
job = json.loads((R/'render_read_job.json').read_text())
root = R/job.get('root', 'SideRepair20261022')
reference = json.loads((R/'FacingRepair20261022/ue_cube_reference.json').read_text())
rv = np.asarray(reference['positions'])
rt = np.asarray(reference['triangles'], int)
reference_volume = np.einsum('ij,ij->i', rv[rt[:, 0]], np.cross(rv[rt[:, 1]], rv[rt[:, 2]])).sum()/6
reference_sign = np.sign(reference_volume)
report = {'scope': 'actual render geometry, both LODs, all six worn backpack assets; not gameplay',
          'facing_reference': reference['asset'], 'reference_signed_volume': reference_volume, 'phases': {}}
for phase in ('Before', 'After'):
    rows = []
    for path in sorted((root/phase).glob('*_render_lod*.json')):
        data = json.loads(path.read_text())
        v = np.asarray(data['positions'])
        f = np.asarray(data['triangles'], int)[np.asarray(data['triangle_materials']) == 0]
        # Match float32 seam copies for diagnosis, without modifying the asset.
        points, remap = np.unique(v.round(4), axis=0, return_inverse=True)
        faces = remap[f]
        used = np.unique(faces)
        compact = np.full(len(points), -1, int)
        compact[used] = np.arange(len(used))
        mesh = trimesh.Trimesh(points[used], compact[faces], process=False)
        edges, counts = np.unique(np.sort(np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0, return_counts=True)
        _, duplicates = np.unique(np.sort(faces, axis=1), axis=0, return_counts=True)
        row = {'file': path.name, 'revision': data['revision'], 'triangles': len(faces),
               'open_edges': int(sum(counts == 1)), 'nonmanifold_edges': int(sum(counts > 2)),
               'duplicate_faces': int(sum(duplicates-1)), 'watertight': bool(mesh.is_watertight),
               'winding_consistent': bool(mesh.is_winding_consistent), 'volume_cm3': float(mesh.volume)}
        row['ue_outward_winding'] = bool(row['volume_cm3']*reference_sign > 0)
        row['passed'] = row['watertight'] and row['winding_consistent'] and row['ue_outward_winding'] and row['duplicate_faces'] == 0
        rows.append(row)
        print('BAG_SIDE_CHECK', phase, row, flush=True)
    report['phases'][phase] = rows
report['passed'] = len(report['phases']['After']) == 12 and all(row['passed'] for row in report['phases']['After'])
(root/'side_checks.json').write_text(json.dumps(report, indent=2))
if not report['passed']:
    raise SystemExit(1)
