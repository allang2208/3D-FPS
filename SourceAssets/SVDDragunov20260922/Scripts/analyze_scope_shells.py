"""Analyse the PSO-1 scope's shells: what parts is it actually built from?

Same evidence-first approach as the rifle body: count connected shells, measure each one,
colour-code the biggest ones and render, so the split into tube / mount / eyepiece /
objective / turrets / illumination housing / lenses follows measured regions.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root> [top_n]
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PALETTE = [
    (1.0, 0.15, 0.15), (0.15, 0.9, 0.2), (0.2, 0.4, 1.0), (1.0, 0.85, 0.1),
    (1.0, 0.3, 0.9), (0.1, 0.9, 0.9), (1.0, 0.55, 0.1), (0.6, 0.3, 1.0),
    (0.4, 1.0, 0.6), (1.0, 0.5, 0.5), (0.5, 0.5, 1.0), (0.8, 0.8, 0.2),
    (0.2, 0.7, 0.4), (1.0, 0.2, 0.5), (0.3, 0.8, 1.0), (0.9, 0.7, 0.3),
]


def shells(obj):
    mesh = obj.data
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
    poly_of = {}
    for poly in mesh.polygons:
        poly_of[poly.index] = find(poly.vertices[0])
    table = {}
    mw = obj.matrix_world
    for poly in mesh.polygons:
        root = poly_of[poly.index]
        entry = table.setdefault(root, {'polys': [], 'min': [1e9] * 3, 'max': [-1e9] * 3})
        entry['polys'].append(poly.index)
        for vi in poly.vertices:
            p = mw @ mesh.vertices[vi].co
            for i in range(3):
                entry['min'][i] = min(entry['min'][i], p[i])
                entry['max'][i] = max(entry['max'][i], p[i])
    return table, poly_of


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    top_n = int(args[1]) if len(args) > 1 else 16
    glb = case / 'Source' / 'svd_source.glb'

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    bpy.context.view_layer.update()
    scope = min((o for o in bpy.context.scene.objects if o.type == 'MESH'),
                key=lambda o: len(o.data.polygons))

    table, poly_of = shells(scope)
    rows = []
    for root, entry in table.items():
        rows.append({
            'island': root, 'polys': len(entry['polys']),
            'center': [round((entry['max'][i] + entry['min'][i]) / 2, 4) for i in range(3)],
            'size': [round(entry['max'][i] - entry['min'][i], 4) for i in range(3)],
            'min': [round(v, 4) for v in entry['min']], 'max': [round(v, 4) for v in entry['max']],
        })
    rows.sort(key=lambda r: -r['polys'])
    print('SCOPE shells=%d polys=%d' % (len(rows), sum(r['polys'] for r in rows)))
    for i, r in enumerate(rows[:40]):
        print('  #%-3d polys=%-5d center=%-26s size=%-26s x=[%+.3f,%+.3f]' %
              (i, r['polys'], r['center'], r['size'], r['min'][0], r['max'][0]))

    # colour the biggest shells for visual identification (source frame: muzzle +Y, up +Z)
    mesh = scope.data
    base = bpy.data.materials.new('base')
    base.use_nodes = True
    base.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.07, 0.07, 0.08, 1)
    mesh.materials.clear()
    mesh.materials.append(base)
    legend = []
    for i, row in enumerate(rows[:top_n]):
        colour = PALETTE[i % len(PALETTE)]
        mat = bpy.data.materials.new('c%d' % i)
        mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*colour, 1)
        mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.6
        mesh.materials.append(mat)
        slot = len(mesh.materials) - 1
        for poly_index in table[row['island']]['polys']:
            mesh.polygons[poly_index].material_index = slot
        legend.append({'index': i, 'island': row['island'], 'polys': row['polys'],
                       'color': [round(c, 3) for c in colour], 'center': row['center'], 'size': row['size']})

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    world = bpy.data.worlds.new('W5')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.25, 0.26, 0.28, 1)
    sun = bpy.data.objects.new('Sun5', bpy.data.lights.new('Sun5', type='SUN'))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(55), 0, math.radians(30))
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new('Cam5')
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new('Cam5', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    centre = Vector((0.165, -0.34, 0.215))
    outdir = case / 'Previews' / 'scope_shells'
    outdir.mkdir(parents=True, exist_ok=True)
    for name, ortho, direction, rot in [
        ('scope_side', 0.50, (1, 0, 0), (math.radians(90), 0, math.radians(90))),
        ('scope_top', 0.50, (0, 0, 1), (0, 0, 0)),
        ('scope_quarter', 0.50, (0.8, -0.45, 0.4), (math.radians(62), 0, math.radians(60))),
    ]:
        cam.data.ortho_scale = ortho
        cam.location = centre + Vector(direction) * 3.0
        cam.rotation_euler = rot
        scene.render.filepath = str(outdir / name)
        bpy.ops.render.render(write_still=True)

    (case / 'Receipts' / 'scope_shells.json').write_text(
        json.dumps({'shell_count': len(rows), 'shells': rows, 'legend': legend}, indent=2), encoding='utf-8')


main()
