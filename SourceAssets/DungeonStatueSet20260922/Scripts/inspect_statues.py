"""Measure and render every statue in Config/statues.json (read-only).

Same author and same photogrammetry export layout as the Diana case: the source OBJ
lives in Source/<key>/source/<Name>_C/<Name>_C.obj next to its atlas PNG, in Z-up
world coordinates with the base far from the origin. Nothing is modified here; the
renders exist to check facing and proportions before the normalisation pass.

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

TILE = 480


def find_source(case, key):
    root = case / 'Source' / key
    objs = sorted(root.rglob('*.obj'))
    if not objs:
        return None, None
    obj = objs[0]
    png = sorted(obj.parent.glob('*.png'))
    return obj, (png[0] if png else None)


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def render_views(case, key, center, span):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.use_denoising = False
    scene.render.resolution_x = TILE
    scene.render.resolution_y = TILE

    world = bpy.data.worlds.new("W_" + key)
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.18, 0.19, 0.21, 1)

    sun = bpy.data.objects.new("Sun_" + key, bpy.data.lights.new("Sun_" + key, type="SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), 0, math.radians(35))
    scene.collection.objects.link(sun)

    cam_data = bpy.data.cameras.new("Cam_" + key)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = span * 1.12
    cam = bpy.data.objects.new("Cam_" + key, cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    outdir = case / 'Previews' / key
    outdir.mkdir(parents=True, exist_ok=True)
    dist = span * 2.0
    views = {
        'from_-Y': ((0, -1, 0), (math.radians(90), 0, 0)),
        'from_+Y': ((0, 1, 0), (math.radians(90), 0, math.radians(180))),
        'from_+X': ((1, 0, 0), (math.radians(90), 0, math.radians(90))),
        'from_-X': ((-1, 0, 0), (math.radians(90), 0, math.radians(-90))),
    }
    paths = {}
    for name, (direction, rot) in views.items():
        cam.location = center + Vector(direction) * dist
        cam.rotation_euler = rot
        scene.render.filepath = str(outdir / name)
        bpy.ops.render.render(write_still=True)
        paths[name] = str(outdir / (name + '.png'))
    # Remove the temporary light/camera so the next statue starts clean.
    for obj in (sun, cam):
        bpy.data.objects.remove(obj, do_unlink=True)
    return paths


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    cfg = json.loads((case / 'Config' / 'statues.json').read_text(encoding='utf-8'))

    report = {'statues': {}}
    for statue in cfg['statues']:
        key = statue['key']
        obj_path, png_path = find_source(case, key)
        if not obj_path:
            print("MISSING SOURCE for", key)
            continue

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.obj_import(filepath=str(obj_path), forward_axis='NEGATIVE_Y', up_axis='Z')
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        tris = 0
        verts = 0
        uv_layers = []
        for o in meshes:
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
            verts += len(o.data.vertices)
            uv_layers += [uv.name for uv in o.data.uv_layers]
        mn, mx = bounds(meshes)
        size = [round(mx[i] - mn[i], 4) for i in range(3)]

        images = [i for i in bpy.data.images if i.size[0] > 0]
        tex = {'count': len(images)}
        if images:
            tex.update({'name': images[0].name, 'width': images[0].size[0], 'height': images[0].size[1]})

        paths = render_views(case, key, (mn + mx) / 2, max(mx - mn))
        entry = {
            'title': statue['title'], 'uid': statue['uid'], 'license': statue['license'],
            'source_obj': str(obj_path), 'source_atlas': str(png_path) if png_path else None,
            'objects': len(meshes), 'verts': verts, 'tris': tris, 'uv_layers': sorted(set(uv_layers)),
            'expected_faces': statue['expected_faces'],
            'bbox_min': [round(v, 4) for v in mn], 'bbox_max': [round(v, 4) for v in mx], 'size': size,
            'longest_axis': int(max(range(3), key=lambda i: size[i])),
            'texture': tex, 'previews': paths,
        }
        report['statues'][key] = entry
        print('STATUE_SCAN', key, json.dumps(entry))

    (case / 'Receipts' / 'source_scan.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')


main()
