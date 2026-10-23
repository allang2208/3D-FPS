"""Replace only the bag portion of the six current sources; preserve R3 straps."""
import hashlib
import json
from pathlib import Path
import numpy as np
from bag_shell import repair, REVISION

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BackpackHarnessRebuild20261020')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, separators=(',', ':')), encoding='utf-8')


manifest = read(R/'manifest.json')
bag = repair(read(R/'Inputs/bag.json'))
write(R/'PreparedBag.json', bag)
receipt = {'revision': REVISION, 'removed_stub_faces': bag['retired_stub_faces'],
           'closed_cuts': bag['shell_caps'], 'bag_triangles': len(bag['triangles']),
           'normal_conversion': [-1, -1, 1], 'winding_reversed': True, 'variants': {}}
for row in manifest['variants']:
    path = Path(row['source'])
    old_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    data = read(path)
    nv, nf = data['harness_vertex_count'], data['harness_face_count']
    bag_bone = next(b['index'] for b in data['bones'] if b['name'] == 'spine_03')
    offset = np.asarray(data['bag_shift'])
    data['positions'] = data['positions'][:nv] + (np.asarray(bag['positions'])+offset).tolist()
    data['weights'] = data['weights'][:nv] + [[[bag_bone, 1.]]] * len(bag['positions'])
    data['triangles'] = data['triangles'][:nf] + (np.asarray(bag['triangles'])+nv).tolist()
    for field in ('uv', 'normals', 'triangle_materials'):
        data[field] = data[field][:nf] + bag[field]
    data.update(revision=REVISION, geometry_convention='cross_e1_e2', bag_cap_face_count=bag['cut_cap_faces'],
                contract='R3 harness unchanged; ' + bag['shell_contract'])
    write(path, data)
    row.update(vertices=len(data['positions']), triangles=len(data['triangles']),
               source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    receipt['variants'][row['profile']] = {'previous_sha256': old_digest,
        'source_sha256': row['source_sha256'], 'harness_vertices_preserved': nv,
        'harness_faces_preserved': nf, 'triangles': row['triangles']}
    print('BAG_SHELL_AUTHORED', row['profile'], row['triangles'], flush=True)
manifest.update(revision=REVISION, save_scope='shell_only', accepted_by_user=False)
write(R/'manifest.json', manifest)
write(R/'FacingRepair20261022/authored.json', receipt)
