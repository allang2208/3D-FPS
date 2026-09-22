"""Colour-code the body's largest shells so each mechanical part can be identified from pixels.

Renders the receiver from the right side with the top shells tinted in distinct colours and
writes a legend (island id -> colour -> bbox). Reading the image then tells us which shell
ids make up the magazine, trigger, charging handle and safety - no guessing.

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
    (0.7, 0.2, 0.8), (0.2, 1.0, 0.9), (1.0, 0.95, 0.6), (0.45, 0.45, 0.45),
    (0.95, 0.35, 0.15), (0.35, 0.95, 0.45), (0.55, 0.35, 0.95), (0.95, 0.75, 0.45),
]


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
    top_n = int(args[1]) if len(args) > 1 else 24
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

    ranked = sorted(stats.items(), key=lambda kv: -kv[1]['polys'])[:top_n]

    # neutral dark base
    base = bpy.data.materials.new('base')
    base.use_nodes = True
    base.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.06, 0.06, 0.07, 1)
    mesh.materials.clear()
    mesh.materials.append(base)

    legend = []
    for i, (root, s) in enumerate(ranked):
        colour = PALETTE[i % len(PALETTE)]
        mat = bpy.data.materials.new('c%d' % i)
        mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*colour, 1)
        mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.6
        mesh.materials.append(mat)
        slot = len(mesh.materials) - 1
        for poly in mesh.polygons:
            if poly_island[poly.index] == root:
                poly.material_index = slot
        legend.append({
            'index': i, 'island': root, 'polys': s['polys'],
            'color': [round(c, 3) for c in colour],
            'center': [round((s['max'][k] + s['min'][k]) / 2, 4) for k in range(3)],
            'size': [round(s['max'][k] - s['min'][k], 4) for k in range(3)],
        })

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    world = bpy.data.worlds.new('W3')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.25, 0.26, 0.28, 1)
    sun = bpy.data.objects.new('Sun3', bpy.data.lights.new('Sun3', type='SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(40))
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new('Cam3')
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new('Cam3', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    outdir = case / 'Previews' / 'shells'
    outdir.mkdir(parents=True, exist_ok=True)
    for name, center, ortho, direction, rot in [
        ('shells_side', (0.0, -0.30, 0.12), 0.95, (1, 0, 0), (math.radians(90), 0, math.radians(90))),
        ('shells_side_rear', (0.0, -0.60, 0.06), 0.85, (1, 0, 0), (math.radians(90), 0, math.radians(90))),
        ('shells_quarter', (0.0, -0.35, 0.10), 0.95, (0.85, -0.5, 0.28), (math.radians(72), 0, math.radians(59))),
    ]:
        cam.data.ortho_scale = ortho
        cam.location = Vector(center) + Vector(direction) * 5.0
        cam.rotation_euler = rot
        scene.render.filepath = str(outdir / name)
        bpy.ops.render.render(write_still=True)

    (case / 'Receipts' / 'shell_colors.json').write_text(json.dumps({'legend': legend}, indent=2), encoding='utf-8')
    for row in legend:
        print('SHELL #%-2d polys=%-6d center=%s size=%s color=%s'
              % (row['index'], row['polys'], row['center'], row['size'], row['color']))


main()
