"""Author aspect-preserved placements of the fine sigil on all six actual blade faces."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P = Path(__file__).resolve().parent
PRODUCTION = P.parent / 'ProductionV1'
sources = json.loads((PRODUCTION / 'blade-layout-source.json').read_text('utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
glyph = bpy.data.images.load(str(P / 'Art/RavenSigilFine.png'))
w, h = glyph.size
pixels = list(glyph.pixels)
aspect = w / h
samples = []
for y in range(0, h, max(1, h // 88)):
    for x in range(0, w, max(1, w // 64)):
        k = 4 * (y * w + x)
        if pixels[k + 3] * max(pixels[k:k + 3]) > .24:
            samples.append(((x + .5) / w - .5, (y + .5) / h - .5))
results = []
for source in sources:
    with bpy.data.libraries.load(source['blend'], link=False) as (_, data):
        data.objects = [source['object']]
    obj = data.objects[0]
    bpy.context.collection.objects.link(obj)
    mesh = obj.data
    bvh = BVHTree.FromPolygons([v.co for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons])
    xmin, xmax = source['bounds'][0]

    def usable(x, z):
        for side in (-1, 1):
            hit, normal, _, _ = bvh.ray_cast(Vector((x, .03 * side, z)), Vector((0, -side, 0)), .06)
            if hit is None or abs(normal.y) < .965:
                return False
        return True

    def center(z):
        hits = [xmin + (xmax - xmin) * i / 360 for i in range(361)
                if usable(xmin + (xmax - xmin) * i / 360, z)]
        return (min(hits) + max(hits)) / 2 if hits else None

    best = None
    for z0 in (.15, .165, .18, .195, .21, .225):
        x0, xa, xb = center(z0), center(z0 - .010), center(z0 + .010)
        if None in (x0, xa, xb):
            continue
        angle = math.atan2(xb - xa, .02)
        c, s = math.cos(angle), math.sin(angle)

        def fits(height):
            for u, v in samples:
                x, z = x0 + (u * c * aspect + v * s) * height, z0 + (-u * s * aspect + v * c) * height
                if not all(usable(x + dx, z + dz) for dx, dz in
                           ((0, 0), (.0011, 0), (-.0011, 0), (0, .0011), (0, -.0011))):
                    return False
            return True

        low, high = .016, .074
        if not fits(low):
            continue
        for _ in range(10):
            middle = (low + high) / 2
            if fits(middle):
                low = middle
            else:
                high = middle
        height = low * .96
        score = height - abs(z0 - .185) * .035
        if best is None or score > best['score']:
            best = {'kind': source['kind'], 'center_cm': [x0 * 100, z0 * 100],
                    'angle_radians': angle, 'width_cm': height * aspect * 100,
                    'height_cm': height * 100, 'source_aspect': aspect, 'score': score}
    if not best:
        raise RuntimeError('No flat-face fit: ' + source['kind'])
    results.append(best)
    print('FINE_RAVEN_FIT ' + json.dumps(best), flush=True)
    bpy.data.objects.remove(obj, do_unlink=True)
text = json.dumps(results, indent=2) + '\n'
(P / 'projection-layouts.json').write_text(text, encoding='utf-8')
(PRODUCTION / 'projection-layouts.json').write_text(text, encoding='utf-8')
