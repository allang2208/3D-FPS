"""Read the five metal claw islands to place bones on the acquired model."""
import json
import struct
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
raw = (ROOT / 'Original/Fisto.glb').read_bytes()
length = struct.unpack_from('<I', raw, 12)[0]
document = json.loads(raw[20:20+length])
binary = raw[28+length:]


def accessor(index):
    a = document['accessors'][index]; view = document['bufferViews'][a['bufferView']]
    dimensions = {'SCALAR':1, 'VEC2':2, 'VEC3':3, 'VEC4':4}[a['type']]
    dtype = {5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
    return np.frombuffer(binary, dtype=dtype, count=a['count']*dimensions,
                         offset=view.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],dimensions)


primitive = document['meshes'][0]['primitives'][0]
points = accessor(primitive['attributes']['POSITION']).astype(float)
indices = accessor(primitive['indices']).reshape(-1,3)
# Join UV-split vertices by position, then recover separate nail islands.
keys = [tuple(np.round(p,5)) for p in points]
parent = {key:key for key in keys}


def find(key):
    while parent[key] != key:
        parent[key] = parent[parent[key]]; key = parent[key]
    return key


for triangle in indices:
    root = find(keys[int(triangle[0])])
    for i in triangle[1:]:
        parent[find(keys[int(i)])] = root
groups = {}
for i,key in enumerate(keys):
    groups.setdefault(find(key),[]).append(i)
landmarks = []
for group in groups.values():
    p = points[group]
    landmarks.append({'vertices':len(group), 'min':p.min(0).tolist(), 'max':p.max(0).tolist(),
                      'center':p.mean(0).tolist(), 'tip':p[np.argmax(p[:,2])].tolist()})
landmarks.sort(key=lambda g:g['center'][0])
(ROOT / 'Export/finger-landmarks.json').write_text(json.dumps(landmarks,indent=2),encoding='utf-8')
print(json.dumps(landmarks,indent=2))
