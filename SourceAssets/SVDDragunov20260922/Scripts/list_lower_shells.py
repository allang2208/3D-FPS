"""List every shell that hangs below the receiver or protrudes on the right side.

That set is exactly the candidate hardware: magazine, trigger + guard, pistol grip,
charging handle, safety lever. Printing their measurements makes the cut regions
evidence-based instead of guessed.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root>
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def islands(mesh):
    parent = list(range(len(mesh.vertices)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for edge in mesh.edges:
        ra, rb = find(edge.vertices[0]), find(edge.vertices[1])
        if ra != rb:
            parent[rb] = ra
    groups = {}
    for v in mesh.vertices:
        groups.setdefault(find(v.index), []).append(v.index)
    return groups


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    glb = case / 'Source' / 'svd_source.glb'

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    bpy.context.view_layer.update()
    body = max((o for o in bpy.context.scene.objects if o.type == 'MESH'),
               key=lambda o: len(o.data.polygons))
    mesh = body.data
    mw = body.matrix_world

    groups = islands(mesh)
    v_island = {}
    for root, idxs in groups.items():
        for vi in idxs:
            v_island[vi] = root
    poly_island = {p.index: v_island[p.vertices[0]] for p in mesh.polygons}

    stats = {}
    for poly in mesh.polygons:
        root = poly_island[poly.index]
        s = stats.setdefault(root, {'polys': 0, 'min': [1e9] * 3, 'max': [-1e9] * 3})
        s['polys'] += 1
        for vi in poly.vertices:
            p = mw @ mesh.vertices[vi].co
            for i in range(3):
                s['min'][i] = min(s['min'][i], p[i])
                s['max'][i] = max(s['max'][i], p[i])

    rows = []
    for root, s in stats.items():
        rows.append({
            'island': root, 'polys': s['polys'],
            'center': [(s['max'][i] + s['min'][i]) / 2 for i in range(3)],
            'size': [s['max'][i] - s['min'][i] for i in range(3)],
            'zmin': s['min'][2], 'zmax': s['max'][2],
            'ymin': s['min'][1], 'ymax': s['max'][1],
            'xmin': s['min'][0], 'xmax': s['max'][0],
        })

    below = sorted([r for r in rows if r['zmin'] < 0.07 and -0.85 < r['center'][1] < 0.1],
                   key=lambda r: r['center'][1])
    right = sorted([r for r in rows if r['xmax'] > 0.188 and r['center'][2] > 0.10],
                   key=lambda r: r['center'][1])

    print('=== shells hanging below z=0.07 (y ascending: stock -> muzzle) ===')
    for r in below:
        print('  island=%-7d polys=%-5d y=[%+.3f,%+.3f] z=[%+.3f,%+.3f] x=[%+.3f,%+.3f] size=[%.3f,%.3f,%.3f]'
              % (r['island'], r['polys'], r['ymin'], r['ymax'], r['zmin'], r['zmax'],
                 r['xmin'], r['xmax'], *r['size']))
    print('=== shells protruding on the right side (x>0.188), z>0.10 ===')
    for r in right:
        print('  island=%-7d polys=%-5d y=[%+.3f,%+.3f] z=[%+.3f,%+.3f] x=[%+.3f,%+.3f] size=[%.3f,%.3f,%.3f]'
              % (r['island'], r['polys'], r['ymin'], r['ymax'], r['zmin'], r['zmax'],
                 r['xmin'], r['xmax'], *r['size']))

    (case / 'Receipts' / 'shells_below.json').write_text(
        json.dumps({'below': below, 'right': right}, indent=2), encoding='utf-8')
    print('counts: below=%d right=%d total_shells=%d' % (len(below), len(right), len(rows)))


main()
