"""Measure tool-axis, blade side and handle cross-sections with signed extents.

Blender --background --python <this> -- <out.json> <a.fbx> [more.fbx ...]
Diagnostic only.
"""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
report = {}
for path in args[1:]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    size = upper - lower
    bands = []
    count = 24
    for band in range(count):
        z0 = lower.z + size.z * band / count
        z1 = lower.z + size.z * (band + 1) / count
        band_points = [p for p in points if z0 <= p.z <= z1]
        if not band_points:
            bands.append({'index': band, 'count': 0})
            continue
        xs = [p.x for p in band_points]
        ys = [p.y for p in band_points]
        bands.append({
            'index': band,
            'z_mid': round((z0 + z1) * .5, 4),
            'count': len(band_points),
            'x_min': round(min(xs), 4), 'x_max': round(max(xs), 4),
            'y_min': round(min(ys), 4), 'y_max': round(max(ys), 4),
            'width_x': round(max(xs) - min(xs), 4),
            'girth_y': round(max(ys) - min(ys), 4),
        })
    name = Path(path).stem
    report[name] = {'file': path, 'vertices': len(points),
                    'triangles': sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons),
                    'min': [round(v, 4) for v in lower], 'max': [round(v, 4) for v in upper],
                    'size': [round(v, 4) for v in size], 'bands': bands}
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))