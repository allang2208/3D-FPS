"""Preserve every face when the smooth-normal cuff uses a shared non-manifold edge."""
import json
from pathlib import Path


def separate_shared_edges(mesh):
    edge_counts = {}
    seen_faces = set()
    separated = 0
    for index, face in enumerate(mesh['triangles']):
        key = tuple(sorted(face))
        edges = [tuple(sorted((face[i], face[(i + 1) % 3]))) for i in range(3)]
        if key in seen_faces or any(edge_counts.get(e, 0) >= 2 for e in edges):
            vertices = []
            for vertex in face:
                vertices.append(len(mesh['positions']))
                mesh['positions'].append(mesh['positions'][vertex])
                mesh['weights'].append(mesh['weights'][vertex])
            mesh['triangles'][index] = vertices
            separated += 1
            continue
        seen_faces.add(key)
        for edge in edges:
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    return separated


if __name__ == '__main__':
    root = Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/Integration')
    manifest = json.loads((root / 'derived.json').read_text(encoding='utf-8'))
    for row in manifest['records']:
        if row['kind'] not in ('pants', 'pants_boot', 'pants_short', 'pants_high'):
            continue
        file = Path(row['file'])
        mesh = json.loads(file.read_text(encoding='utf-8'))
        count = separate_shared_edges(mesh)
        if count:
            file.write_text(json.dumps(mesh, separators=(',', ':')), encoding='utf-8')
        print(row['kind'], row['rig'], count, flush=True)
