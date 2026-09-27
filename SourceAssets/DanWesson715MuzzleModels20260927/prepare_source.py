"""Extract the existing game's front silhouette for authoring two virtual meshes."""
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).parent
SRC = OUT.parent / 'DanWesson715GripBrake20260927/FitInspection/host.json'
host = json.loads(SRC.read_text(encoding='utf-8'))
refs = {k: np.array(v) for k, v in host['reference'].items()}
up = refs['WPN_root'][:3, 2]
up /= np.linalg.norm(up)
forward = refs['WPN_FrontSight'][:3, 3] - refs['WPN_RearSight'][:3, 3]
forward -= up * np.dot(up, forward)
forward /= np.linalg.norm(forward)
frame = np.eye(4)
frame[:3, :3] = np.column_stack((forward, np.cross(up, forward), up))
frame[:3, 3] = refs['WPN_SOCKET_Muzzle'][:3, 3]
v = (np.array(host['positions']) - frame[:3, 3]) @ frame[:3, :3]
v *= np.array([.01, -.01, .01])
triangles = np.array(host['triangles'], dtype=int)
indices = [i for i, m in enumerate(host['materials'])
           if host['slots'][m] in ('M_DW715_Hero_Steel', 'M_DW715_Hero_Frame')]
sections = {}
for x in [-.024, -.018, -.012, -.006, -.001]:
    points = []
    for i in indices:
        tri = v[triangles[i]]
        for j in range(3):
            a, b = tri[j], tri[(j + 1) % 3]
            if (a[0] - x) * (b[0] - x) < 0:
                p = a + (b - a) * ((x - a[0]) / (b[0] - a[0]))
                points.append([float(p[1]), float(p[2])])
    sections[str(x)] = points

record = {'source_snapshot': str(SRC), 'host_asset': host['asset'],
          'ue_mount_matrix': frame.tolist(), 'frame': 'Blender metres, +X forward, +Z up, origin WPN_SOCKET_Muzzle',
          'sections': sections, 'material_paths': host['material_paths'],
          'reference_only': 'Existing game render geometry, not physical fabrication data'}
(OUT / 'source_frame.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
summary = {x: {'points': len(p), 'min_yz': np.min(p, axis=0).tolist(),
               'max_yz': np.max(p, axis=0).tolist()} for x, p in sections.items() if p}
print('DW715_FRONT_SOURCE ' + json.dumps(summary), flush=True)
