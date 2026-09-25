"""Bake V7 field-glove leather regions and hem/construction stitches.

Uses the shared M4 fitted-glove authoring UV. Palm/dorsal comes from the same
digit-local back vector as the fit script. Stitches follow the cuff opening and
the geometric palm-to-dorsal join, not UV cuts.
"""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

PROJECT = Path('D:/FPS3D/FPSGAME')
GLOVE = json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored/M4.json').read_text())
ANATOMY = json.loads((PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json').read_text())['anatomy']
OUT = PROJECT/'SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 4096
SCAN_M = 0.25


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def smooth(a, b, v):
    t = np.clip((v-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def vertex_normals(p, t):
    corners = p[t]
    face = -unit(np.cross(corners[:, 1]-corners[:, 0], corners[:, 2]-corners[:, 0]))
    result = np.zeros_like(p)
    for k in range(3):
        a = unit(corners[:, (k+1) % 3]-corners[:, k])
        b = unit(corners[:, (k+2) % 3]-corners[:, k])
        angle = np.arccos(np.clip((a*b).sum(1), -1, 1))
        np.add.at(result, t[:, k], face*angle[:, None])
    return unit(result)


p_cm = np.asarray(GLOVE['positions'], dtype=np.float64)
p = p_cm * 0.01
t = np.asarray(GLOVE['triangles'], dtype=np.int32)
uv = np.asarray(GLOVE['uv'], dtype=np.float64)
weights = GLOVE['weights']
n = vertex_normals(p, t)

dorsal = np.zeros_like(p)
for side, frame in ANATOMY.items():
    belongs = p[:, 0] < 0 if side == 'l' else p[:, 0] > 0
    digit_dorsal = {d['bone']: np.asarray(d['dorsal'], dtype=np.float64) for d in frame['digits']}
    for vi in np.flatnonzero(belongs):
        w = weights[vi]
        total = sum(value for name, value in w.items() if name in digit_dorsal)
        dorsal[vi] = np.asarray(frame['dorsal'], dtype=np.float64)*max(0, 1-total)
        for name, value in w.items():
            if name in digit_dorsal:
                dorsal[vi] += digit_dorsal[name]*value
dorsal = unit(dorsal)
back = smooth(-.15, .65, (n*dorsal).sum(1))
face_back = back[t].mean(1)
palm_faces = face_back < 0.42

corners = p[t]
mesh_area = 0.5*np.linalg.norm(np.cross(corners[:, 1]-corners[:, 0], corners[:, 2]-corners[:, 0]), axis=1).sum()
uv_area = 0.5*np.abs(
    uv[:, 0, 0]*(uv[:, 1, 1]-uv[:, 2, 1]) +
    uv[:, 1, 0]*(uv[:, 2, 1]-uv[:, 0, 1]) +
    uv[:, 2, 0]*(uv[:, 0, 1]-uv[:, 1, 1])).sum()
uv_per_metre = math.sqrt(uv_area/max(mesh_area, 1e-12))
tile = math.sqrt(mesh_area/max(uv_area, 1e-12))/SCAN_M
px_per_metre = uv_per_metre * SIZE

edge_uses = Counter()
edge_uv = {}
for fi, face in enumerate(t):
    loops = uv[fi]
    inside = loops.mean(0)
    for k in range(3):
        a, b = int(face[k]), int(face[(k+1) % 3])
        key = tuple(sorted((a, b)))
        edge_uses[key] += 1
        edge_uv[key] = {
            'a': loops[k].tolist(), 'b': loops[(k+1) % 3].tolist(),
            'inside': inside.tolist(), 'length': float(np.linalg.norm(p[a]-p[b])),
            'palm': bool(palm_faces[fi]),
            'transition': bool((back[a] < 0.35 and back[b] > 0.55) or (back[b] < 0.35 and back[a] > 0.55)),
        }

cuff = [key for key, count in edge_uses.items() if count == 1]
transition = [key for key, data in edge_uv.items() if data['transition'] and edge_uses[key] == 2]


def chains(keys):
    adj = defaultdict(list)
    for a, b in keys:
        adj[a].append(b)
        adj[b].append(a)
    remaining = set(keys)
    result = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        path = [start[0], start[1]]
        while True:
            end = path[-1]
            nxt = None
            for other in adj[end]:
                edge = tuple(sorted((end, other)))
                if edge in remaining:
                    nxt = other
                    remaining.remove(edge)
                    break
            if nxt is None:
                break
            path.append(nxt)
        result.append(path)
    return result


def segments_from_edges(keys, skip_palm=False):
    segs = []
    for path in chains(keys):
        distance = 0.0
        for i in range(len(path)-1):
            a, b = path[i], path[i+1]
            data = edge_uv[tuple(sorted((a, b)))]
            if skip_palm and data['palm']:
                distance += data['length']
                continue
            segs.append({**data, 'distance': distance})
            distance += data['length']
    return segs


seam_segments = segments_from_edges(cuff, skip_palm=False) + segments_from_edges(transition, skip_palm=True)


def pixel(uv_xy):
    return (uv_xy[0]*(SIZE-1), (1-uv_xy[1])*(SIZE-1))


glove = Image.new('L', (SIZE, SIZE), 0)
palm = Image.new('L', (SIZE, SIZE), 0)
stitches = Image.new('L', (SIZE, SIZE), 0)
dg, dp, ds = ImageDraw.Draw(glove), ImageDraw.Draw(palm), ImageDraw.Draw(stitches)
for fi, face_uv in enumerate(uv):
    points = [pixel(pt) for pt in face_uv]
    dg.polygon(points, fill=255)
    if palm_faces[fi]:
        dp.polygon(points, fill=255)

pitch, dash, inset_m, width_m = 0.0032, 0.0019, 0.0012, 0.00048
width = max(1, round(width_m*px_per_metre))
for seg in seam_segments:
    if seg['length'] < 1e-7:
        continue
    a, b, c = np.asarray(seg['a']), np.asarray(seg['b']), np.asarray(seg['inside'])
    tangent = b-a
    inward = np.array([-tangent[1], tangent[0]])
    inward /= max(np.linalg.norm(inward), 1e-9)
    if np.dot(inward, c-(a+b)/2) < 0:
        inward = -inward
    inset = inward * inset_m * uv_per_metre
    start, end = seg['distance'], seg['distance']+seg['length']
    for n in range(math.floor(start/pitch), math.ceil(end/pitch)+1):
        lo, hi = max(start, n*pitch), min(end, n*pitch+dash)
        if hi <= lo:
            continue
        p0 = a+tangent*((lo-start)/seg['length'])+inset
        p1 = a+tangent*((hi-start)/seg['length'])+inset
        ds.line([pixel(p0), pixel(p1)], fill=255, width=width)

stitches = ImageChops.multiply(stitches, glove)
glove = glove.filter(ImageFilter.MaxFilter(9))
palm = palm.filter(ImageFilter.MaxFilter(9))
stitches = stitches.filter(ImageFilter.GaussianBlur(0.55))
Image.merge('RGB', (glove, palm, stitches)).save(OUT/'T_FieldGloves_LeatherRegions.png')

height = np.asarray(stitches, dtype=np.float32)/255
dy, dx = np.gradient(height)
nx, ny = -dx*0.65, -dy*0.65
nz = np.ones_like(nx)
norm = np.sqrt(nx*nx+ny*ny+nz*nz)
normal = np.stack((nx/norm, ny/norm, nz/norm), axis=-1)
Image.fromarray(np.uint8(np.clip((normal*0.5+0.5)*255, 0, 255))).save(OUT/'T_FieldGloves_StitchNormal.png')

metrics = {
    'source': str(PROJECT/'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored/M4.json'),
    'vertices': int(len(p)), 'triangles': int(len(t)),
    'mesh_area_m2': float(mesh_area), 'uv_area': float(uv_area),
    'scan_width_metres': SCAN_M,
    'leather_uv_repeat_for_25cm_scan': float(tile),
    'palm_faces': int(palm_faces.sum()),
    'cuff_edges': len(cuff), 'transition_edges': len(transition),
    'stitch_pitch_metres': pitch, 'stitch_width_metres': width_m,
    'mask_channels': {'R': 'all gloves', 'G': 'palm and finger pads', 'B': 'cuff hem and palm-dorsal join stitches'},
    'normal_convention': 'DirectX; do not flip green in UE',
}
(OUT/'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n', encoding='utf-8')
print(json.dumps(metrics), flush=True)
