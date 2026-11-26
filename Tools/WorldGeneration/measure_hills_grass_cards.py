"""Measure LOD0 blade-card coverage using the shipped Quixel UVs, mesh areas and alpha atlas."""
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[2] / 'SourceAssets'
source = root / 'HillsSoftGrass20261112/Prepared'
atlas = root / 'HillsRainforestCarpet20261111/WildTufts/Textures/T_vlkhcbxia_1K_B-O.png'
out = root / 'HillsEcologyUpgrade20261114/Cutout/leaf-card-geometry.json'


def mesh_arrays(path):
    raw = path.read_bytes()
    length, = struct.unpack_from('<I', raw, 12)
    doc = json.loads(raw[20:20 + length])
    primitive, = doc['meshes'][0]['primitives']
    def accessor(index):
        field = doc['accessors'][index]
        view = doc['bufferViews'][field['bufferView']]
        width = {'VEC3': 3, 'VEC2': 2, 'SCALAR': 1}[field['type']]
        dtype = {5123: '<u2', 5126: '<f4'}[field['componentType']]
        return np.frombuffer(raw, dtype, field['count'] * width,
                             28 + length + view['byteOffset']).reshape(-1, width)
    attr = primitive['attributes']
    return accessor(attr['POSITION']), accessor(attr['TEXCOORD_0']), accessor(primitive['indices']).reshape(-1, 3)


def coverage(path, mask):
    pos, uv, faces = mesh_arrays(path)
    triangles = pos[faces]
    areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
    # Uniform centroids of equal-area subtriangles. Sample the same bilinear alpha the material clips.
    n = 16
    pairs = [(i + 1/3, j + 1/3) for i in range(n) for j in range(n-i)]
    pairs += [(i + 2/3, j + 2/3) for i in range(n-1) for j in range(n-1-i)]
    a, b = (np.array(pairs) / n).T
    coords = np.stack([a, b, 1-a-b], axis=1) @ uv[faces]
    h, w = mask.shape
    pixels = coords * (w, h) - .5
    idx = np.floor(pixels).astype(int)
    dx, dy = (pixels - idx).transpose(2, 0, 1)
    x, y = idx.transpose(2, 0, 1)
    alpha = ((1-dx)*(1-dy)*mask[y % h, x % w] + dx*(1-dy)*mask[y % h, (x+1) % w]
             + (1-dx)*dy*mask[(y+1) % h, x % w] + dx*dy*mask[(y+1) % h, (x+1) % w])
    visible = (alpha >= .28*255).mean(axis=1)
    return dict(mesh=path.stem, triangles=len(faces), samples_per_triangle=n*n,
                estimated_masked_out_area_percent=round(float(np.average(1-visible, weights=areas)*100), 2),
                triangles_without_visible_samples=int((visible == 0).sum()))


if __name__ == '__main__':
    with Image.open(atlas) as image:
        mask = np.asarray(image.getchannel('A'))
    measurements = [coverage(source / (name+'.glb'), mask) for name in ('SM_SoftWildGrassLow', 'SM_SoftWildGrassTuft')]
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(measurements, indent=2), encoding='utf-8')
    print(measurements)
