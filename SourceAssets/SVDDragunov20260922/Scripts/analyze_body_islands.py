"""Split the SVD body into mechanical parts by loose-shell analysis.

The source ships one body mesh with the magazine, bolt, charging handle, trigger and
safety all fused into it. The weapon workflow requires those to keep separate mechanical
identities, so this finds the mesh's connected shells, measures each one, and prints a
per-shell table (plus renders an overlay) BEFORE anything is cut - the classification is
evidence-based, not guessed.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def islands(mesh):
    """Connected components over edges, as vertex-index sets."""
    parent = list(range(len(mesh.vertices)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for edge in mesh.edges:
        union(edge.vertices[0], edge.vertices[1])
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
    body = None
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and len(o.data.polygons) > 10000:
            body = o
    if body is None:
        raise RuntimeError('body mesh not found')

    # SVD convention frame: length +Y (muzzle), up +Z, right +X
    mesh = body.data
    mult = body.matrix_world
    groups = islands(mesh)
    verts_of = {i: [] for i in range(len(mesh.polygons))}
    poly_island = {}
    v_index_island = {}
    for root, idxs in groups.items():
        for vi in idxs:
            v_index_island[vi] = root
    for poly in mesh.polygons:
        poly_island[poly.index] = v_index_island[poly.vertices[0]]

    stats = {}
    for poly in mesh.polygons:
        root = poly_island[poly.index]
        s = stats.setdefault(root, {'polys': 0, 'min': [1e9] * 3, 'max': [-1e9] * 3})
        s['polys'] += 1
        for vi in poly.vertices:
            p = mult @ mesh.vertices[vi].co
            for i in range(3):
                s['min'][i] = min(s['min'][i], p[i])
                s['max'][i] = max(s['max'][i], p[i])

    rows = []
    for root, s in stats.items():
        size = [s['max'][i] - s['min'][i] for i in range(3)]
        center = [(s['max'][i] + s['min'][i]) / 2 for i in range(3)]
        rows.append({
            'island': root, 'polys': s['polys'],
            'size': [round(v, 4) for v in size],
            'center': [round(v, 4) for v in center],
            'min': [round(v, 4) for v in s['min']],
            'max': [round(v, 4) for v in s['max']],
        })
    rows.sort(key=lambda r: -r['polys'])

    total_polys = sum(r['polys'] for r in rows)
    print('SVD_BODY islands=%d polys=%d' % (len(rows), total_polys))
    for i, r in enumerate(rows[:40]):
        print('  #%-3d polys=%-6d center=%-26s size=%s' % (i, r['polys'], r['center'], r['size']))

    (case / 'Receipts').mkdir(exist_ok=True)
    (case / 'Receipts' / 'body_islands.json').write_text(json.dumps(
        {'island_count': len(rows), 'total_polys': total_polys, 'islands': rows}, indent=2), encoding='utf-8')


main()
