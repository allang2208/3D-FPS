"""Requested saved front-face checks calibrated against UE's own cube."""
import json
from pathlib import Path
import numpy as np
import trimesh

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BackpackHarnessRebuild20261020')
root = R/'FacingRepair20261022'
cube = json.loads((root/'ue_cube_reference.json').read_text())
cv, ct = np.asarray(cube['positions']), np.asarray(cube['triangles'], int)
cube_normals = np.cross(cv[ct[:, 2]]-cv[ct[:, 0]], cv[ct[:, 1]]-cv[ct[:, 0]])
cube_dot = np.einsum('ij,ij->i', cube_normals, np.asarray(cube['normals']).mean(1))
if not np.all(cube_dot > 0):
    raise RuntimeError('UE reference does not agree with the specified front-face rule')
report = {'reference': cube['asset'], 'ue_front_face': 'cross_e2_e1',
          'scope': 'saved render mesh front faces, both LODs; no gameplay capture', 'phases': {}}
for phase, directory in [('Before', R/'SideRepair20261022/After'), ('After', root/'After')]:
    rows = []
    for path in sorted(directory.glob('*_render_lod*.json')):
        data = json.loads(path.read_text())
        v, t = np.asarray(data['positions']), np.asarray(data['triangles'], int)
        mats, normals = np.asarray(data['triangle_materials']), np.asarray(data['normals'])
        face_normals = np.cross(v[t[:, 2]]-v[t[:, 0]], v[t[:, 1]]-v[t[:, 0]])
        lengths = np.linalg.norm(face_normals, axis=1)
        face_normals /= np.maximum(lengths[:, None], 1e-12)
        normal_dot = np.einsum('ij,ij->i', face_normals, normals.mean(1))
        wrong = (lengths > 1e-8) & (normal_dot < -1e-4)
        bag_triangles = t[mats == 0]
        mesh = trimesh.Trimesh(v, bag_triangles, process=False)
        used = np.unique(bag_triangles)
        low, high = v[used].min(0), v[used].max(0)
        side_samples = []
        for axis in (0, 1):
            other = [i for i in range(3) if i != axis]
            a, b = np.meshgrid(np.linspace(low[other[0]]+.5, high[other[0]]-.5, 9),
                               np.linspace(low[other[1]]+.5, high[other[1]]-.5, 13))
            for sign in (-1, 1):
                starts = np.zeros((a.size, 3))
                starts[:, other[0]], starts[:, other[1]] = a.ravel(), b.ravel()
                starts[:, axis] = low[axis]-10 if sign == 1 else high[axis]+10
                directions = np.zeros_like(starts)
                directions[:, axis] = sign
                first = mesh.ray.intersects_first(starts, directions)
                hit = first >= 0
                dot = np.einsum('ij,ij->i', face_normals[mats == 0][first[hit]], directions[hit])
                side_samples.append({'axis': axis, 'direction': sign, 'hits': int(hit.sum()),
                                     'first_surface_backfacing': int(sum(dot > 1e-6))})
        row = {'file': path.name, 'revision': data['revision'],
               'bag_faces_opposed_to_ue_normals': int(sum(wrong & (mats == 0))),
               'harness_faces_opposed_to_ue_normals': int(sum(wrong & (mats > 0))),
               'side_samples': side_samples}
        row['passed'] = not wrong.any() and all(s['hits'] > 0 and s['first_surface_backfacing'] == 0 for s in side_samples)
        rows.append(row)
        print('BAG_FRONT_FACE', phase, path.name, 'wrong normals', int(wrong.sum()),
              'first backfaces', sum(s['first_surface_backfacing'] for s in side_samples), flush=True)
    report['phases'][phase] = rows
report['passed'] = len(report['phases']['After']) == 12 and all(r['passed'] for r in report['phases']['After'])
(root/'front_face_checks.json').write_text(json.dumps(report, indent=2))
if not report['passed']:
    raise SystemExit(1)
