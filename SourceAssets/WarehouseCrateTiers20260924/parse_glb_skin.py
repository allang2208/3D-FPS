"""Parse the source GLB: authoritative skin data (joints, inverse binds, mesh->skin, anim channels).

The Blender 5.1 gltf importer silently drops armatures/vgroups for this file, so we read the
GLB chunks directly: struct header -> JSON chunk -> BIN chunk. Emits glb_skin_report.json with
everything needed to rebuild the rig in cm space: node world transforms, skins with joint node
indices + inverseBindMatrices, per-mesh primitive attributes (JOINTS_0/WEIGHTS_0 presence),
and animation channel/sampler tables (which node rotates for Open/Close and the key frame range).
"""
import json, struct, base64, array
from pathlib import Path

GLB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ChestRitual20260909\warehouse_chest_ritual_v8.glb')
OUT = Path(__file__).parent / 'glb_skin_report.json'

data = GLB.read_bytes()
assert data[:4] == b'glTF', data[:4]
off = 12
json_chunk = None
bin_chunk = b''
while off < len(data):
    ln, typ = struct.unpack_from('<II', data, off)
    off += 8
    payload = data[off:off + ln]
    if typ == 0x4E4F534A:  # JSON
        json_chunk = json.loads(payload.decode('utf-8'))
    elif typ == 0x004E4942:
        bin_chunk = payload
    off += ln
g = json_chunk
buffers = g.get('buffers', [])
assert not buffers or buffers[0].get('uri') is None, 'expected embedded bin'

def read_accessor(idx, count=None):
    a = g['accessors'][idx]
    comp_t = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}[a['componentType']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    bv = g['bufferViews'][a['bufferView']]
    start = a.get('byteOffset', 0) + bv.get('byteOffset', 0)
    cnt = count if count is not None else a['count']
    stride = bv.get('byteStride', n * struct.calcsize(comp_t))
    out = []
    for i in range(cnt):
        base = start + i * stride
        vals = array.array(comp_t)
        vals.frombytes(bin_chunk[base:base + n * struct.calcsize(comp_t)])
        out.append(list(vals))
    return out

report = {'meshes': {}, 'nodes': [], 'skins': [], 'anims': {}}
# nodes with transforms + world matrices
def node_world(ni, parent_mat):
    n = g['nodes'][ni]
    t = n.get('translation', [0, 0, 0]); r = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1])
    import math
    # quaternion (x,y,z,w) -> 3x3
    x, y, z, w = r
    lm = math.sqrt(x*x + y*y + z*z + w*w) or 1.0
    x, y, z, w = x/lm, y/lm, z/lm, w/lm
    rot = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
           [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
           [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    local = [[rot[0][0]*s[0], rot[0][1]*s[1], rot[0][2]*s[2], t[0]],
             [rot[1][0]*s[0], rot[1][1]*s[1], rot[1][2]*s[2], t[1]],
             [rot[2][0]*s[0], rot[2][1]*s[1], rot[2][2]*s[2], t[2]],
             [0, 0, 0, 1]]
    def mul(A, B):
        return [[sum(A[i][k]*B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
    world = mul(parent_mat, local) if parent_mat else local
    report['nodes'].append({'index': ni, 'name': n.get('name', str(ni)), 'mesh': n.get('mesh'),
                            'skin': n.get('skin'), 'world': world})
    for c in n.get('children', []):
        node_world(c, world)

roots = [i for i in range(len(g['nodes'])) if i not in {c for n in g['nodes'] for c in n.get('children', [])}]
for r0 in roots:
    node_world(r0, None)

for si, sk in enumerate(g.get('skins', [])):
    ibm = read_accessor(sk['inverseBindMatrices']) if 'inverseBindMatrices' in sk else None
    report['skins'].append({'index': si, 'name': g['nodes'][sk['solver']].get('name') if sk.get('solver') is not None else None,
                            'joints': [sk_j for sk_j in sk['joints']],
                            'joint_names': [g['nodes'][j].get('name', str(j)) for j in sk['joints']],
                            'inverse_bind': ibm})

for mi, m in enumerate(g['meshes']):
    prims = []
    for p in m['primitives']:
        attrs = p['attributes']
        prims.append({'attrs': list(attrs.keys()),
                      'pos_count': g['accessors'][attrs['POSITION']]['count'],
                      'material': p.get('material'),
                      'mode': p.get('mode', 4)})
    report['meshes'][g['meshes'][mi].get('name', str(mi))] = prims

for ai, an in enumerate(g.get('animations', [])):
    chans = []
    for c in an['channels']:
        node = c['target']['node']
        chans.append({'node': node, 'node_name': g['nodes'][node].get('name', str(node)),
                      'path': c['target']['path'], 'sampler': c['sampler']})
    samplers = []
    for s in an['samplers']:
        inp = read_accessor(s['input']); outp = read_accessor(s['output'])
        samplers.append({'interp': s['interpolation'], 'input': inp, 'output': outp,
                         'output_type': g['accessors'][s['output']]['type'],
                         'key_count': len(inp)})
    report['anims'][an.get('name', str(ai))] = {'channels': chans, 'samplers': samplers}

OUT.write_text(json.dumps(report, indent=1), encoding='utf-8')
print('GLB_REPORT_DONE', 'nodes', len(report['nodes']), 'skins', len(report['skins']),
      'anims', list(report['anims'].keys()), flush=True)
