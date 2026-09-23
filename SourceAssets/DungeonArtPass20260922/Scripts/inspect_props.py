"""Inspect the seven prop sources: geometry, slots, size, orientation.

Sources are heterogeneous (FBX with PBR sets, OBJ without materials, one .blend), so
this only handles geometry and material slot names - texture wiring is declared in
Config/props.json and applied on the UE side.

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

# key -> (relative mesh path under Source/<key>, format)
SOURCES = {
    'lantern': ('source/Lantern01.fbx', 'fbx'),
    'cobwebs': ('source/Test 1.obj', 'obj'),
    'ladder': ('source/Stool/Stool.fbx', 'fbx'),
    'rope': ('source/Rope2.blend', 'blend'),
    'extinguisher': ('source/hasiaci-low/hasiaci-low.obj', 'obj'),
    'bucket': ('source/Bucket_low.fbx', 'fbx'),
    'barrel': ('source/Oil_Barrel.fbx', 'fbx'),
}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path, fmt):
    if fmt == 'fbx':
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif fmt == 'obj':
        bpy.ops.wm.obj_import(filepath=str(path), forward_axis='NEGATIVE_Y', up_axis='Z')
    elif fmt == 'blend':
        bpy.ops.wm.open_mainfile(filepath=str(path))
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    report = {}

    for key, (rel, fmt) in SOURCES.items():
        path = case / 'Source' / key / rel
        if not path.exists():
            print('MISSING', key, path)
            continue
        reset()
        meshes = load(path, fmt)
        if not meshes:
            print('NO_MESH', key)
            continue
        tris = 0
        slots = []
        for o in meshes:
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
            slots += [s.material.name if s.material else None for s in o.material_slots]
        mn, mx = bounds(meshes)
        size = [round(mx[i] - mn[i], 4) for i in range(3)]
        entry = {
            'format': fmt, 'path': str(path), 'objects': len(meshes),
            'object_names': [o.name for o in meshes][:8],
            'tris': tris, 'material_slots': slots,
            'bbox_min': [round(v, 4) for v in mn], 'bbox_max': [round(v, 4) for v in mx],
            'size': size, 'longest_axis': int(max(range(3), key=lambda i: size[i])),
            'images': sorted({i.name for i in bpy.data.images if i.size[0] > 0}),
        }
        report[key] = entry
        print('PROP_SCAN', key, json.dumps(entry))

        # One orthographic view from -Y per prop so orientation can be judged.
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 8
        scene.cycles.use_denoising = False
        scene.render.resolution_x = 460
        scene.render.resolution_y = 460
        world = bpy.data.worlds.new('W_' + key)
        scene.world = world
        world.use_nodes = True
        world.node_tree.nodes['Background'].inputs[0].default_value = (0.18, 0.19, 0.21, 1)
        sun = bpy.data.objects.new('Sun_' + key, bpy.data.lights.new('Sun_' + key, type='SUN'))
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(55), 0, math.radians(35))
        scene.collection.objects.link(sun)
        cam_data = bpy.data.cameras.new('Cam_' + key)
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = max(size) * 1.15
        cam = bpy.data.objects.new('Cam_' + key, cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam
        center = (mn + mx) / 2
        outdir = case / 'Previews' / key
        outdir.mkdir(parents=True, exist_ok=True)
        for name, (direction, rot) in {
            'from_-Y': ((0, -1, 0), (math.radians(90), 0, 0)),
            'from_+X': ((1, 0, 0), (math.radians(90), 0, math.radians(90))),
        }.items():
            cam.location = center + Vector(direction) * max(size) * 2.0
            cam.rotation_euler = rot
            scene.render.filepath = str(outdir / name)
            bpy.ops.render.render(write_still=True)

    (case / 'Receipts').mkdir(exist_ok=True)
    (case / 'Receipts' / 'source_scan.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')


main()
