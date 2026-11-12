"""Folded individual blades in metre-scale glTF and the three Fab scans."""
import json
import math
import random
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Prepared'
OUT.mkdir(exist_ok=True)
PROFILES = (('LowSward', 76, .24, .16, .010),
            ('RibbonGrass', 59, .22, .30, .013),
            ('BankSedge', 43, .17, .44, .011))


def glb(name, doc, data):
    data = bytes(data) + bytes(-len(data) % 4)
    doc['buffers'] = [{'byteLength': len(data)}]
    header = json.dumps(doc, separators=(',', ':')).encode()
    header += b' ' * (-len(header) % 4)
    (OUT / (name + '.glb')).write_bytes(
        struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(data)) +
        struct.pack('<I4s', len(header), b'JSON') + header +
        struct.pack('<I4s', len(data), b'BIN\x00') + data)


def grass(profile, index, lod):
    kind, total, radius, height, width = profile
    rng = random.Random(4701 + index)
    roots = []
    for _ in range(9):
        az, r = rng.uniform(0, math.tau), radius * rng.random()**.5
        roots.append(np.array([math.cos(az)*r, 0., math.sin(az)*r]))
    vertices, normals, uvs, traits, triangles = [], [], [], [], []
    for i in range(total):
        root = roots[i % len(roots)] + np.array([rng.uniform(-.045,.045), 0., rng.uniform(-.045,.045)])
        theta = rng.uniform(0, math.tau)
        height_i = height * rng.uniform(.55,1.12)
        reach = height_i * rng.uniform(.35,1.75)
        half_width = width * rng.uniform(.54,1.34)
        twist, tint, keep = rng.uniform(-.86,.86), rng.random(), rng.random()
        broad = index == 0 and i % 8 == 1
        if broad:
            half_width *= 2.6
        if keep > (1.,.52,.25)[lod]:
            continue
        half_width *= (1.,1.16,1.36)[lod]
        axis = np.array([math.cos(theta),0.,math.sin(theta)])
        start = len(vertices)
        sections = ((0.,.48),(.34,1.),(.70,.66)) if lod < 2 else ((0.,.52),(.49,.89))
        for t, shape in sections:
            side = np.array([-math.sin(theta+twist*t),0.,math.cos(theta+twist*t)])
            center = root + axis*(reach*t**1.65)
            center[1] = height_i*(1.65*t-.68*t*t)
            w = half_width*shape*(max(.17,math.sin(math.pi*t)) if broad else 1.)
            for k in (-1,0,1):
                p = center + side*(k*w)
                p[1] += (.32*w if k == 0 else 0.)
                vertices.append(p)
                n = np.array([-.13*axis[0]+k*.26*side[0], .92, -.13*axis[2]+k*.26*side[2]])
                normals.append(n/np.linalg.norm(n))
                uvs.append(((k+1)*.5,t));traits.append((tint,1. if broad else 0.))
        tip = root + axis*reach
        tip[1] = height_i*(.68 if reach>height_i else .96)
        last = len(vertices)
        vertices.append(tip);normals.append((0.,1.,0.));uvs.append((.5,1.));traits.append((tint,1. if broad else 0.))
        for row in range(len(sections)-1):
            for k in range(2):
                a = start+row*3+k
                triangles.extend((a,a+1,a+3,a+1,a+4,a+3))
        a=last-3
        triangles.extend((a,a+1,last,a+1,a+2,last))

    name = 'SM_' + kind + (f'_LOD{lod}' if lod else '')
    data,views,access = bytearray(),[],[]
    def add(values, shape, is_index=False, position=False):
        a=np.asarray(values,dtype='<u2' if is_index else '<f4')
        data.extend(bytes(-len(data)%4))
        views.append({'buffer':0,'byteOffset':len(data),'byteLength':a.nbytes,'target':34963 if is_index else 34962})
        record={'bufferView':len(views)-1,'componentType':5123 if is_index else 5126,'count':len(a),'type':shape}
        if position:record.update(min=a.min(0).tolist(),max=a.max(0).tolist())
        access.append(record);data.extend(a.tobytes());return len(access)-1
    attr={'POSITION':add(vertices,'VEC3',position=True),'NORMAL':add(normals,'VEC3'),
          'TEXCOORD_0':add(uvs,'VEC2'),'TEXCOORD_1':add(traits,'VEC2')}
    prim={'attributes':attr,'indices':add(triangles,'SCALAR',True)}
    doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
         'nodes':[{'name':name,'mesh':0}],'meshes':[{'name':name,'primitives':[prim]}],
         'accessors':access,'bufferViews':views}
    glb(name,doc,data)


for index,profile in enumerate(PROFILES):
    for lod in range(3):
        grass(profile,index,lod)
for directory in ('MossyForestBoulder','ForestTwig01','ForestTwig02'):
    src=next((ROOT/directory).glob('*.gltf'))
    doc=json.loads(src.read_text(encoding='utf8'))
    data=(src.parent/doc['buffers'][0]['uri']).read_bytes()
    for key in ('materials','images','textures','samplers','extensionsUsed','extensionsRequired','extensions'):
        doc.pop(key,None)
    for mesh in doc['meshes']:
        for prim in mesh['primitives']:
            prim.pop('material',None)
        mesh['name']='SM_'+directory
    doc['nodes'][0]['name']='SM_'+directory
    glb('SM_'+directory,doc,data)

# The publisher's last LOD is a whole-plant billboard. Keep three actual
# leaf-mesh LODs and omit the billboard, including at the far culling distance.
ginger=next((ROOT/'JungleGinger').glob('*.gltf'))
source=json.loads(ginger.read_text(encoding='utf8'))
buffer=(ginger.parent/source['buffers'][0]['uri']).read_bytes()
for variant in ('D','E'):
    for lod in range(3):
        original='SM_sgbms_Var'+variant+(f'_LOD{lod}' if lod else '')
        node=next(n for n in source['nodes'] if n['name']==original)
        name='SM_JungleGinger'+variant+(f'_LOD{lod}' if lod else '')
        prims=[]
        for prim in source['meshes'][node['mesh']]['primitives']:
            if prim['material']!=0:raise ValueError('Billboard in selected leaf LOD')
            prims.append({k:v for k,v in prim.items() if k!='material'})
        doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
             'nodes':[{**node,'name':name,'mesh':0}],
             'meshes':[{'name':name,'primitives':prims}],'accessors':source['accessors'],'bufferViews':source['bufferViews']}
        glb(name,doc,buffer)
