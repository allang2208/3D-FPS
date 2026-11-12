"""Recover the cross pin from the original atlas and match its native receiver faces."""
import hashlib
import json
from pathlib import Path
import pickle
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
sys.path.insert(0, str(SOURCE))
from source_geometry import read_primitives

RIG = '/Game/Weapons/M249/SK_M249_V7'
BASE = '/Game/Weapons/M249/Bipod/SM_M249_Bipod_Base'
BODY = '/Game/Weapons/M249/Assembly/SM_M249_body'
TABLE = '/Game/Weapons/M249/Assembly/SM_M249_bipod'

def main():
    _, positions, normals, uv, faces, islands = next(read_primitives())
    vertices, indices = np.unique(faces[islands == 22], return_inverse=True)
    indices = indices.reshape(-1, 3)
    def component(raw):
        return np.asarray(raw, dtype=float)[:, [1, 0, 2]] * 100 + [5.45, -28.6, -5.3]
    points = component(positions[vertices])
    with (SOURCE/'Wrist33/geometry.pkl').open('rb') as stream:
        rig = pickle.load(stream)
    receiver = np.array(rig['faces'])[np.array(rig['sections']) == rig['slots'].index('M249_Factory_Receiver')]
    centers = np.asarray(rig['vertices'])[receiver].mean(1)
    dist, native = cKDTree(centers).query(points[indices].mean(1))
    if len(indices) != 50 or len(set(native)) != len(indices) or dist.max() >= .001:
        raise ValueError('The source pin does not match the captured receiver')
    old_receiver = component(np.load(SOURCE/'Geometry/Receiver.npz')['positions'])
    pivot = (old_receiver.min(0) + old_receiver.max(0)) * .5
    fit = json.loads((SOURCE/'GripMount40/fit.json').read_text())
    info = dict(component=points.tolist(), normals=normals[vertices][:, [1,0,2]].tolist(),
                uv=uv[vertices].tolist(), faces=indices.tolist(), centers=centers[native].tolist(),
                body_pivot=pivot.tolist(), root_position=fit['root_position'], root_rotation=fit['root_rotation'])
    (HERE/'pin.json').write_text(json.dumps(info,separators=(',',':')))
    files = {path: SOURCE.parents[1]/'Content'/(path[6:]+'.uasset') for path in (RIG,BASE,BODY,TABLE)}
    inputs = {path: hashlib.sha256(file.read_bytes()).hexdigest() for path,file in files.items()}
    stamp = HERE/'inputs.json'
    if not stamp.exists():
        stamp.write_text(json.dumps(inputs, indent=2))

if __name__ == '__main__':
    main()
