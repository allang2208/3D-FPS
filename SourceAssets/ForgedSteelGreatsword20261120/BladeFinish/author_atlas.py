"""Bake the factory steel in the selected Meshy sword's original UV atlas."""
import json
import struct
import sys
from pathlib import Path

import cv2
import numpy as np
from numba import njit
from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'Integration'
sys.path.insert(0, str(HERE.parent / 'GuardSeatFinish'))
from seat_profile import contains
inside_seat = njit(contains)
raw = next((SOURCE / 'Original').glob('*.glb')).read_bytes()
json_size, = struct.unpack_from('<I', raw, 12)
gltf = json.loads(raw[20:20 + json_size])
prim = gltf['meshes'][0]['primitives'][0]


def accessor(index):
    item = gltf['accessors'][index]
    view = gltf['bufferViews'][item['bufferView']]
    dtype = np.dtype({5123: '<u2', 5125: '<u4', 5126: '<f4'}[item['componentType']])
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[item['type']]
    offset = 28 + json_size + view.get('byteOffset', 0) + item.get('byteOffset', 0)
    return np.ndarray((item['count'], width), dtype=dtype, buffer=raw, offset=offset,
                      strides=(view.get('byteStride', width * dtype.itemsize), dtype.itemsize))


triangles = accessor(prim['indices']).reshape(-1, 3)
xyz = accessor(prim['attributes']['POSITION'])
uv = accessor(prim['attributes']['TEXCOORD_0'])
fit = json.loads((SOURCE / 'fit_manifest.json').read_text(encoding='utf-8'))
FIT_CM = 100. * fit['uniform_scale']
# Invert prepare_model.py's source-Y to fitted-Z transform at the actual guard seam.
shoulder = (fit['cuts_z_cm']['blade_guard'] / 100 + .05) / fit['uniform_scale'] - .548
tip = float(xyz[:, 1].max())
fractions = (np.arange(512) + .5) / 512


def blade_outline():
    edges = xyz[triangles][:, [0, 1, 2, 1, 2, 0]].reshape(-1, 6, 3)
    start, end = edges[:, :3].reshape(-1, 3), edges[:, 3:].reshape(-1, 3)
    outline = []
    for y in shoulder + fractions * (tip - shoulder):
        crosses = (start[:, 1] < y) != (end[:, 1] < y)
        a, b = start[crosses], end[crosses]
        x = a[:, 0] + (y - a[:, 1]) * (b[:, 0] - a[:, 0]) / (b[:, 1] - a[:, 1])
        outline.append(((x.min() + x.max()) / 2, (x.max() - x.min()) / 2))
    return np.array(outline)


@njit
def bake_pixels(src, coords, points, faces, bounds, cut, top, packed):
    h, w = src.shape[:2]
    result = src.copy()
    # 0 is gutter, 1 is original hilt, 2 is newly authored steel.
    ownership = np.zeros((h, w), np.uint8)
    for ids in faces:
        u, v = coords[ids, 0] * w - .5, coords[ids, 1] * h - .5
        det = (v[1]-v[2])*(u[0]-u[2]) + (u[2]-u[1])*(v[0]-v[2])
        if abs(det) < 1e-9:
            continue
        for row in range(max(0, int(np.ceil(v.min()))), min(h, int(np.floor(v.max())) + 1)):
            for col in range(max(0, int(np.ceil(u.min()))), min(w, int(np.floor(u.max())) + 1)):
                a = ((v[1]-v[2])*(col-u[2]) + (u[2]-u[1])*(row-v[2])) / det
                b = ((v[2]-v[0])*(col-u[2]) + (u[0]-u[2])*(row-v[2])) / det
                c = 1-a-b
                if min(a,b,c) < -1e-6:
                    continue
                y = a*points[ids[0],1] + b*points[ids[1],1] + c*points[ids[2],1]
                x = a*points[ids[0],0] + b*points[ids[1],0] + c*points[ids[2],0]
                if y < cut and not inside_seat((x + .00045) * FIT_CM, (y + .548) * FIT_CM - 5.):
                    ownership[row,col] = 1
                    result[row,col] = src[row,col]
                    continue
                ownership[row,col] = 2
                section = max(0, min(len(bounds)-1, int((y-cut)/(top-cut)*len(bounds))))
                center, radius = bounds[section]
                across = min(1., abs(x-center) / max(.0001,radius))
                bevel = min(1., max(0., (across-.79)/.15))
                bevel *= bevel*(3.-2.*bevel)
                # Fine lengthwise grind marks run continuously across UV seams.
                phase = x*7200. + 1.7*np.sin(y*6.3) + .38*np.sin(y*22. + x*88.)
                grain = .65*np.sin(phase) + .35*np.sin(phase*1.417 + .6)
                if packed:
                    variation = float(src[row,col,1])-95.
                    result[row,col,1] = min(159., max(50., 121. + .9*variation + 7.*grain - bevel*(49.+3.*grain)))
                    result[row,col,2] = min(247., max(209., 225.+.22*(float(src[row,col,2])-214.) + 17.*bevel))
                else:
                    luma = .213*src[row,col,0] + .715*src[row,col,1] + .072*src[row,col,2]
                    steel = min(173., max(73., 109.+.48*(luma-134.) + 1.8*grain + 30.*bevel))
                    result[row,col,0] = steel-2.
                    result[row,col,1] = steel
                    result[row,col,2] = steel+1.
    return result, ownership


def pad_islands(color, ownership):
    # Extend the nearest surface into its own empty UV border for mip filtering.
    empty = (ownership == 0).astype(np.uint8)
    dist, labels = cv2.distanceTransformWithLabels(empty, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    occupied = np.nonzero(ownership)
    owner = np.empty(labels.max()+1, dtype=np.int32)
    owner[labels[occupied]] = np.ravel_multi_index(occupied, ownership.shape)
    margin = (empty != 0) & (dist <= 10)
    yy, xx = np.nonzero(margin)
    nearest = owner[labels[yy,xx]]
    use = ownership.ravel()[nearest] == 2
    color[yy[use],xx[use]] = color.reshape(-1,3)[nearest[use]]


outline = blade_outline()
for channel in ('BaseColor', 'MetallicRoughness'):
    pixels = np.array(Image.open(SOURCE / 'Textures' / f'ForgedSteelGreatsword_{channel}.jpg').convert('RGB'))
    color, owners = bake_pixels(pixels, uv, xyz, triangles, outline, shoulder, tip, channel == 'MetallicRoughness')
    pad_islands(color, owners)
    Image.fromarray(color).save(HERE / f'ForgedSteelGreatsword_{channel}.png', compress_level=5)
