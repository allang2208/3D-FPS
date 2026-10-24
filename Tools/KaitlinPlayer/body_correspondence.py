"""Resolve native body topology by UV identity before transferring coverage."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from body_surface_fit import bind_warp

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')


def correspond(source, target):
    source_uv = json.loads((WORK / 'jason_body_uv.json').read_text())['vertex_uvs']
    target_uv = json.loads((WORK / 'kaitlin_body_uv.json').read_text())['vertex_uvs']
    lookup = defaultdict(list)
    for vertex, uvs in source_uv.items():
        lookup[tuple(map(tuple, uvs))].append(int(vertex))
    warped = bind_warp(source, target)
    target_points = np.asarray(target['positions'])
    mapping = np.full(len(target_points), -1, int)
    used = set()
    for vertex, uvs in target_uv.items():
        vertex = int(vertex)
        candidates = [v for v in lookup[tuple(map(tuple, uvs))] if v not in used]
        if not candidates:
            raise RuntimeError('Native UV topology needs an explicit correspondence at vertex ' + str(vertex))
        selected = min(candidates, key=lambda v: np.linalg.norm(warped[v] - target_points[vertex]))
        mapping[vertex] = selected
        used.add(selected)
    if np.any(mapping < 0) or len(used) != len(source['positions']):
        raise RuntimeError('Body coverage requires a complete one-to-one topology map.')
    triangles = {tuple(sorted(triangle)): index for index, triangle in enumerate(source['triangles'])}
    incident = defaultdict(list)
    source_faces = np.asarray(source['triangles'], int)
    for face, triangle in enumerate(source_faces):
        for vertex in triangle:
            incident[vertex].append(face)
    face_map = []
    retessellated = 0
    for triangle in np.asarray(target['triangles'], int):
        key = tuple(sorted(mapping[triangle]))
        if key in triangles:
            face_map.append(triangles[key])
            continue
        # Native exports can triangulate a quad along the other diagonal.
        # Resolve its coverage from the adjacent source triangles, maintaining
        # anatomical UV identity instead of copying unrelated triangle IDs.
        candidates = set(face for vertex in key for face in incident[vertex])
        center = warped[list(key)].mean(axis=0)
        selected = min(candidates, key=lambda face: (
            -len(set(source_faces[face]).intersection(key)),
            np.linalg.norm(warped[source_faces[face]].mean(axis=0) - center)))
        face_map.append(selected)
        retessellated += 1
    print('KAITLIN_BODY_UV_TOPOLOGY', len(mapping), 'vertices;', retessellated, 'retessellated triangles', flush=True)
    return mapping, np.asarray(face_map, int)


if __name__ == '__main__':
    inputs = WORK / 'FitInputs'
    body = json.loads((inputs / 'player_body.json').read_text(encoding='utf-8-sig'))
    modular = json.loads((inputs / 'modular_outfits.json').read_text(encoding='utf-8-sig'))
    captured = json.loads((inputs / 'captured.json').read_text())
    source_path = modular['profiles'][body['body_mesh']]['native_bare_skin']
    source = json.loads((inputs / captured[source_path]['file']).read_text())
    target = json.loads((WORK / 'NativeGeometry/MHC_Kaitlin_Body.json').read_text())
    vertices, triangles = correspond(source, target)
    (WORK / 'body_correspondence.json').write_text(json.dumps({
        'source': source_path, 'target': target['source'],
        'target_to_source_vertices': vertices.tolist(), 'target_to_source_triangles': triangles.tolist(),
        'method': 'native_uv_identity_and_triangle_topology'}, separators=(',', ':')), encoding='utf-8')
    print('KAITLIN_BODY_CORRESPONDENCE_AUTHORED', len(vertices), len(triangles))
