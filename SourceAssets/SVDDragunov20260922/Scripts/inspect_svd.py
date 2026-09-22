"""Inspect the SVD glb: geometry, per-slot extents, size, orientation.

Blender 5.1 no longer ships the Collada add-on, so the author's model.dae is paired with
Sketchfab's glb for geometry (same mesh: 25,440 + 6,049 tris, two material slots). The
source's two texture sets are svd_* (rifle) and pso_* (PSO-1 scope); per-slot bounding
boxes tell which slot is the scope so the sets can be assigned deterministically.

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


def slot_stats(obj):
    """World-space bbox per material slot, computed from the faces using that slot."""
    stats = {}
    mesh = obj.data
    mesh.calc_loop_triangles()
    mw = obj.matrix_world
    for poly in mesh.polygons:
        s = stats.setdefault(poly.material_index, {'min': [1e9] * 3, 'max': [-1e9] * 3, 'polys': 0})
        s['polys'] += 1
        for vi in poly.vertices:
            p = mw @ mesh.vertices[vi].co
            for i in range(3):
                s['min'][i] = min(s['min'][i], p[i])
                s['max'][i] = max(s['max'][i], p[i])
    for idx, s in stats.items():
        s['size'] = [round(s['max'][i] - s['min'][i], 4) for i in range(3)]
        s['center'] = [round((s['max'][i] + s['min'][i]) / 2, 4) for i in range(3)]
        s['min'] = [round(v, 4) for v in s['min']]
        s['max'] = [round(v, 4) for v in s['max']]
    return stats


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    glb = next((case / 'Source').rglob('*.glb'))
    if not glb.exists():
        glb = Path('D:/FPS3D/_sketchfab_goddess/svd') / 'glb_svd_dragunov_sniper_rifle.glb'
    print('SOURCE_GLB', glb)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    report = {'source': str(glb), 'objects': [], 'tris': 0}
    for o in meshes:
        o.data.calc_loop_triangles()
        report['tris'] += len(o.data.loop_triangles)
        slots = [s.material.name if s.material else None for s in o.material_slots]
        report['objects'].append({
            'name': o.name, 'tris': len(o.data.loop_triangles), 'verts': len(o.data.vertices),
            'slots': slots, 'slot_stats': {str(k): v for k, v in slot_stats(o).items()},
            'uv_layers': [uv.name for uv in o.data.uv_layers],
        })
    mn, mx = bounds(meshes)
    report['bbox_min'] = [round(v, 4) for v in mn]
    report['bbox_max'] = [round(v, 4) for v in mx]
    report['size'] = [round(mx[i] - mn[i], 4) for i in range(3)]
    report['longest_axis'] = int(max(range(3), key=lambda i: report['size'][i]))
    report['images'] = sorted({i.name for i in bpy.data.images if i.size[0] > 0})
    print('SVD_SCAN', json.dumps(report))

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 10
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 860
    scene.render.resolution_y = 420
    world = bpy.data.worlds.new('W')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.18, 0.19, 0.21, 1)
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', type='SUN'))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(55), 0, math.radians(35))
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new('Cam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(report['size']) * 1.08
    cam = bpy.data.objects.new('Cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    center = (mn + mx) / 2
    outdir = case / 'Previews'
    outdir.mkdir(parents=True, exist_ok=True)
    for name, (direction, rot) in {
        'side_from_-Y': ((0, -1, 0), (math.radians(90), 0, 0)),
        'side_from_+Y': ((0, 1, 0), (math.radians(90), 0, math.radians(180))),
        'top_from_+Z': ((0, 0, 1), (0, 0, 0)),
        'muzzle_from_+X': ((1, 0, 0), (math.radians(90), 0, math.radians(90))),
    }.items():
        cam.location = center + Vector(direction) * max(report['size']) * 1.8
        cam.rotation_euler = rot
        scene.render.filepath = str(outdir / name)
        bpy.ops.render.render(write_still=True)

    (case / 'Receipts').mkdir(exist_ok=True)
    (case / 'Receipts' / 'source_scan.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')


main()
