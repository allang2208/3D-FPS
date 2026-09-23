"""Re-import every exported FBX and check the round trip, then render four views.

Canaries (from project history):
  * triangle/vertex counts must match the source export,
  * max angle between loop normals sharing a vertex stays near 0 deg (a flat-shaded
    export would jump to face-to-face angles),
  * the base must sit at Z=0 with the pivot on the base centre.

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


def max_loop_angle(mesh):
    corners = mesh.corner_normals
    per_vert = {}
    for loop in mesh.loops:
        per_vert.setdefault(loop.vertex_index, []).append(Vector(corners[loop.index].vector))
    worst = 0.0
    for normals in per_vert.values():
        base = normals[0]
        for n in normals[1:]:
            if base.length and n.length:
                worst = max(worst, base.angle(n))
    return math.degrees(worst)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    cfg = json.loads((case / 'Config' / 'statues.json').read_text(encoding='utf-8-sig'))
    report = {'statues': {}}

    for statue in cfg['statues']:
        key = statue['key']
        fbx = case / 'Authored' / (statue['mesh_name'] + '.fbx')
        if not fbx.exists():
            print('MISSING_FBX', key)
            continue

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(fbx))
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        tris = 0
        worst = 0.0
        for o in meshes:
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
            worst = max(worst, max_loop_angle(o.data))
        pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        size = [round(mx[i] - mn[i], 5) for i in range(3)]

        entry = {
            'objects': len(meshes), 'tris': tris,
            'max_loop_normal_angle_deg': round(worst, 2),
            'bbox_min': [round(v, 5) for v in mn], 'bbox_max': [round(v, 5) for v in mx],
            'size_m': size,
            'uv_layers': sorted({uv.name for o in meshes for uv in o.data.uv_layers}),
            'materials': sorted({s.material.name if s.material else None for o in meshes for s in o.material_slots}),
        }

        scene = bpy.context.scene
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 8
        scene.cycles.use_denoising = False
        scene.render.resolution_x = TILE
        scene.render.resolution_y = TILE
        world = bpy.data.worlds.new("W")
        scene.world = world
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs[0].default_value = (0.18, 0.19, 0.21, 1)
        sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(55), 0, math.radians(35))
        scene.collection.objects.link(sun)
        cam_data = bpy.data.cameras.new("Cam")
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = max(size) * 1.12
        cam = bpy.data.objects.new("Cam", cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam
        center = (mn + mx) / 2
        dist = max(size) * 2.0
        outdir = case / 'Previews' / (key + '_final')
        outdir.mkdir(parents=True, exist_ok=True)
        views = {
            'from_-Y': ((0, -1, 0), (math.radians(90), 0, 0)),
            'from_+X': ((1, 0, 0), (math.radians(90), 0, math.radians(90))),
            'from_+Y': ((0, 1, 0), (math.radians(90), 0, math.radians(180))),
            'from_-X': ((-1, 0, 0), (math.radians(90), 0, math.radians(-90))),
        }
        for name, (direction, rot) in views.items():
            cam.location = center + Vector(direction) * dist
            cam.rotation_euler = rot
            scene.render.filepath = str(outdir / name)
            bpy.ops.render.render(write_still=True)
        entry['previews'] = str(outdir)

        report['statues'][key] = entry
        print('VERIFY_STATUE', key, json.dumps(entry))

    (case / 'Receipts' / 'verify_fbx.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')


main()
