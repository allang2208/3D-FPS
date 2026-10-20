"""Solve the offset between the audit's frame and the glTF accessor frame.

The audit reports landmarks in the FBX node space; the mesh vertices are the raw
glTF POSITION accessor values. Lengths match to 0.01 cm but the frames are
translated, so every audit landmark needs this offset before it can be used
against the vertices. Prints the constants used by author_svch.py.
"""
import json
from pathlib import Path

import numpy as np

O = Path(__file__).parent
import struct

GLB = O / 'download' / 'svch.glb'
CT = {5120: ('i1', 1), 5121: ('u1', 1), 5122: ('i2', 2), 5123: ('u2', 2),
      5125: ('u4', 4), 5126: ('f4', 4)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

src = open(GLB, 'rb').read()
_, _, length = struct.unpack_from('<III', src, 0)
off, chunks = 12, []
while off < length:
    clen, ctype = struct.unpack_from('<II', src, off)
    chunks.append((ctype, off + 8, clen))
    off += 8 + clen
J = json.loads(src[chunks[0][1]:chunks[0][1] + chunks[0][2]].decode('utf-8'))
BIN = src[chunks[1][1]:chunks[1][1] + chunks[1][2]]


def acc(i):
    a = J['accessors'][i]
    bv = J['bufferViews'][a['bufferView']]
    dt, sz = CT[a['componentType']]
    n = NC[a['type']]
    st = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride') or sz * n
    cnt = a['count']
    if stride == sz * n:
        return np.frombuffer(BIN, dtype=np.dtype(dt), count=cnt * n, offset=st).reshape(cnt, n)
    return np.array([np.frombuffer(BIN, dtype=np.dtype(dt), count=n,
                                   offset=st + i * stride) for i in range(cnt)])


V = []
for m in J['meshes']:
    pr = m['primitives'][0]
    V.append(acc(pr['attributes']['POSITION']).astype('float64'))
V = np.vstack(V)
lo, hi = V.min(0), V.max(0)

measurements = json.loads((O / 'audit' / 'measurements.json').read_text(encoding='utf-8'))
S = measurements['landmarks']

# Barrel axis: the audit puts it at (Y=0, Z=5.5755). The same axis in the glTF
# frame is the centre of the free barrel, which is the only tube ahead of the
# handguard and inboard of the brake.
# Muzzle cap: the audit reports its centre and radius, so the cap here is
# whatever sits at max X. That pins the bore centre on both lateral axes
# without depending on island guesses.
cap = V[V[:, 0] > (hi[0] - 1.6)]
cy = float((cap[:, 1].min() + cap[:, 1].max()) * 0.5)
cz = float((cap[:, 2].min() + cap[:, 2].max()) * 0.5)
r_y = float(cap[:, 1].max() - cap[:, 1].min()) * 0.5
r_z = float(cap[:, 2].max() - cap[:, 2].min()) * 0.5

dx = float(S['muzzle_tip']['point'][0]) - float(hi[0])   # audit X  = glTF X + dx
dz = float(S['bore_axis']['point'][2]) - cy              # audit Z  = glTF Y + dz
dy = 0.0                                                 # audit Y  = glTF Z (lateral, centred)

print('gltf bbox x [%.3f, %.3f]  y [%.3f, %.3f]  z [%.3f, %.3f]' %
      (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
print('muzzle cap centre  y=%.4f  z=%.4f  (radii %.3f / %.3f)' % (cy, cz, r_y, r_z))
print('audit muzzle x=%.3f  bore z=%.4f' % (S['muzzle_tip']['point'][0],
                                            S['bore_axis']['point'][2]))
print('OFFSET audit->gltf: dx=%.4f dy=%.4f dz=%.4f' % (dx, dy, dz))
print('OFFSET check butt: gltf min x %.3f + dx = %.3f  vs audit %.3f' %
      (lo[0], lo[0] + dx, S['stock_butt_plate']['centre'][0]))
print('OFFSET check sight top: gltf max y %.3f + dz = %.3f vs audit %.3f' %
      (hi[1], hi[1] + dz, S['rear_sight_top'] if 'rear_sight_top' in S else 14.765))

out = {'gltf_bbox': {'min': [round(float(v), 4) for v in lo],
                     'max': [round(float(v), 4) for v in hi]},
       'barrel_centre_gltf': [round(cy, 4), round(cz, 4)],
       'offset_audit_to_gltf': {'dx': round(dx, 4), 'dy': round(dy, 4), 'dz': round(dz, 4)}}
(O / 'Auditing' if False else O / 'Authoring').mkdir(exist_ok=True)
(O / 'Authoring' / 'frame_offset.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
