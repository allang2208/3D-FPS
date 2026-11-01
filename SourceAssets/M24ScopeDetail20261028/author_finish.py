"""Write UV0 finish-control data without changing geometry or structural normals."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

O = Path(__file__).resolve().parent
T = O / 'Textures'
T.mkdir(exist_ok=True)
geometry = json.loads((O / 'scope_geometry.json').read_text(encoding='utf-8'))
size = 2048
image = Image.new('RGB', (size, size), (0, 0, 0))
coverage = Image.new('L', (size, size), 0)
draw, cover = ImageDraw.Draw(image), ImageDraw.Draw(coverage)
counts = Counter()
recipes = {
    'tube': (.37, .59, 0),
    'turret': (.32, .57, 0),
    'knurled_ring': (.40, .62, 0),
    'mount': (.43, .60, 0),
    'eyepiece': (.35, .64, 0),
    'interior': (.68, .74, 0),
}
for tri in geometry['triangles']:
    x, y, z = tri['center']
    nx, _, nz = tri['normal']
    region = 'tube'
    if z < .153:
        region = 'mount'
    elif (.225 < y < .271 and z > .208) or (.228 < y < .268 and x > .035):
        region = 'turret'
    elif .277 < y < .412:
        region = 'knurled_ring'
    elif y < .015:
        region = 'eyepiece'
    if (y < .003 or y > .413) and nx * (x + .00025) + nz * (z - .1778) < -.001:
        region = 'interior'
    points = [(u * (size - 1), (1 - v) * (size - 1)) for u, v in tri['uv']]
    draw.polygon(points, fill=tuple(round(v * 255) for v in recipes[region]))
    cover.polygon(points, fill=255)
    counts[region] += 1
pixels = np.asarray(image).copy()
inside = np.asarray(coverage) > 0
expanded = np.asarray(image.filter(ImageFilter.MaxFilter(17)))
margin = (~inside) & (np.asarray(coverage.filter(ImageFilter.MaxFilter(17))) > 0)
pixels[margin] = expanded[margin]
pixels[(~inside) & (~margin)] = (round(.40 * 255), round(.59 * 255), 0)
Image.fromarray(pixels).save(T / 'T_M24_ScopeDetail_Regions.png')
(O / 'finish_recipe.json').write_text(json.dumps({
    'texture': 'T_M24_ScopeDetail_Regions', 'size': size, 'uv': 0,
    'channels': ['metal roughness', 'dielectric roughness', 'preserved source colour override'],
    'regions': recipes, 'triangles': counts,
    'structural_normal': 'Retained T_M24_Scope_Refined_N; OpenGL source, UE green flip once',
    'identity': 'Original SourceORM B continues to define metal/dielectric identity',
    'source_markings': 'Existing regional master preserves source light markings',
    'geometry_changed': False,
}, indent=2), encoding='utf-8')
print('M24_SCOPE_FINISH_AUTHORED', dict(counts))
