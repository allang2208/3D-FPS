"""Build short nape locks on the exported active scalp; run in background Blender."""
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

source_file, output_folder = sys.argv[sys.argv.index('--') + 1:]
out = Path(output_folder)
source = json.loads(Path(source_file).read_text(encoding='utf-8'))
positions = np.asarray(source['positions'])
triangles = np.asarray(source['triangles'])
tree = BVHTree.FromPolygons([Vector(p) for p in positions], triangles.tolist(), all_triangles=True)
rng = np.random.default_rng(211115)
collar_top = source['collar_top']
hairline = max(146.4, collar_top + 1.9)
vertices, normals, uv, weights, faces = [], [], [], [], []

def scalp(theta, z, lift):
    direction = Vector((math.sin(theta), -math.cos(theta), 0))
    center = Vector((0, 0, z))
    hit, normal, face, _ = tree.ray_cast(center + direction * 21, -direction, 20)
    if hit is None:
        raise ValueError(f'Scalp surface missing at angle {theta:.3f} and height {z:.3f}')
    if normal.dot(direction) < 0:
        normal.negate()
    tri = triangles[face]
    a, b, c = positions[tri]
    local, _, _, _ = np.linalg.lstsq(np.column_stack((b-a, c-a)), np.asarray(hit)-a, rcond=None)
    bary = np.maximum([1-local.sum(), *local], 0)
    influences = {}
    for idx, mix in zip(tri, bary / bary.sum()):
        for bone, weight in source['weights'][idx]:
            influences[bone] = influences.get(bone, 0) + weight * mix
    ordered = sorted(((bone, w) for bone, w in influences.items() if w > .0001),
                     key=lambda pair: -pair[1])[:8]
    total = sum(weight for _, weight in ordered)
    return list(hit + normal * lift), list(normal), [[bone, weight/total] for bone, weight in ordered]

def lock(angle, layer, index):
    # Keep the upper band under the existing low bun. Break its sharp lower edge
    # with overlapping swept underhair and a sparse final layer of loose wisps.
    side = abs(angle) / 1.4
    fine = layer == 2
    start = (rng.uniform(152.1, 155.7) if fine else rng.uniform(155.0, 158.7)) + 1.45 * side
    end = hairline + 4.1*side**1.65 + .35*math.cos(4.2*angle) + rng.uniform(-.38, .45)
    if fine:
        end -= rng.uniform(.35, 1.25)
    else:
        end += .5*layer
    end = max(end, collar_top + 1.35)
    drift = math.sin(angle)*rng.uniform(.09,.28) + rng.normal(0,.042)
    flutter = rng.uniform(-.045,.045)
    width = rng.uniform(.56,.87) if layer==0 else rng.uniform(.37,.64) if layer==1 else rng.uniform(.10,.23)
    tile = (index + 2*layer) % 4
    first = len(vertices)
    sections = 10
    for j in range(sections + 1):
        t = j / sections
        theta = angle - drift*t + flutter*math.sin(math.pi*t)
        z = start + (end - start)*t
        taper = .86 + .21*math.sin(math.pi*t) - .45*t**2
        for i in range(3):
            across = i-1
            # Keep the ribbons close to the scalp. The arched cross-section
            # separates neighbouring locks and catches light along the sweep.
            lift = .055 + .037*layer + (1-across**2)*(.035+.035*math.sin(math.pi*t))
            if fine:
                lift += .115*t*t
            p, n, w = scalp(theta + across*width*taper / (2*max(4.7, 7.1-2.1*t)), z, lift)
            vertices.append(p); normals.append(n); weights.append(w)
            uv.append([(tile+.025+.95*i/2)/4, .005+.99*t])
        if j:
            row = first+j*3
            for i in (0,1):
                a = row-3+i; b = row+i
                faces.extend([[a,b,a+1],[a+1,b,b+1]])
for layer, count in enumerate([35, 30, 28]):
    for i in range(count):
        theta = -1.40 + 2.80*(i+rng.uniform(.13,.86))/count
        lock(theta, layer, i)
geometry = dict(positions=vertices,normals=normals,uv=uv,weights=weights,triangles=faces,bone_names=source['bone_names'])
(out/'nape_cards.json').write_text(json.dumps(geometry,separators=(',',':')),encoding='utf-8')

# Four independent longitudinal fibre masks. Random ends break the lower
# silhouette; a fuller interior survives mip filtering away from the camera.
h, tile_width = 1024, 256
rgba = np.zeros((h,tile_width*4,4),dtype=np.uint8)
v = np.arange(h)/(h-1)
xx = (np.arange(tile_width)+.5)/tile_width
for tile in range(4):
    density = np.zeros((h,tile_width))
    shade = np.zeros((h,tile_width))+.48
    wave = math.sin(1.9*tile)*.043*np.sin(v*math.pi)
    width = .38*(1-.68*v**1.8)
    for n in range(98):
        root = rng.uniform(-.43,.43)
        phase = rng.uniform(-math.pi,math.pi)
        end = rng.uniform(.67,1.07) - .14*abs(root)
        bend = rng.uniform(-.075,.075)
        centers = (.50+root*(1-.58*v**1.7)+wave + bend*v**1.5 +
                   .013*np.sin(phase+4.1*v)*np.sin(v*math.pi))*tile_width
        radius = rng.uniform(.66,1.30)*(1-.36*v)*np.clip((end-v)/.13,0,1)
        ids = np.arange(h)
        brightness = rng.uniform(.14,.94)
        for offset in range(-2,3):
            x = np.clip(np.floor(centers).astype(int)+offset,0,tile_width-1)
            strength = np.clip(radius+.47-np.abs(x+.5-centers),0,1)*np.clip((end-v)*58,0,1)
            shade[ids,x] = shade[ids,x]*(1-strength)+brightness*strength
            density[ids,x] = np.maximum(density[ids,x], strength)
    inner = np.clip((width[:,None] - np.abs(xx[None,:]-.5-wave[:,None]))/.12,0,1)
    inner *= .78*np.clip((.84-v[:,None])/.17,0,1)
    alpha = np.maximum(density, inner)*np.clip(v[:,None]*40+.02,0,1)
    rgb = (np.array([21,16,14])+shade[...,None]*np.array([24,18,14]))*(.87+.13*v[:,None,None])
    rgba[:,tile*tile_width:(tile+1)*tile_width,:3] = np.rint(rgb).astype('u1')
    rgba[:,tile*tile_width:(tile+1)*tile_width,3] = np.rint(255*alpha).astype('u1')
def chunk(kind, raw):
    return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw))
raw = b''.join(b'\x00'+row.tobytes() for row in rgba)
(out/'T_Nun_NapeFibres_R10.png').write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',tile_width*4,h,8,6,0,0,0))+
    chunk(b'IDAT',zlib.compress(raw,8))+chunk(b'IEND',b''))
(out/'authored.json').write_text(json.dumps(dict(revision='NapeHairR10',locks=93,triangles=len(faces),
    collar_top_cm=collar_top,lowest_hair_cm=min(v[2] for v in vertices),
    head=source['head'],collar=source['collar'],atlas_tiles=4),indent=2),encoding='utf-8')
print('NUN_NAPE_CARDS_AUTHORED',len(faces),flush=True)
