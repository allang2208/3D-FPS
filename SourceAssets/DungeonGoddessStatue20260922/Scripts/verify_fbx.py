"""Re-import the exported FBX and check that shading survived the round trip.

The project has a recorded failure where a rebuilt mesh exported with flat normals
(111k hard edges lost, "distorted/rough" in engine). The canary is the maximum
angle between loop normals sharing a vertex: a smooth scan stays near 0 deg, a
faceted export jumps to face-to-face angles.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <fbx> <reference_png_out>
"""
import sys
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector


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
    fbx, out_png = args[0], args[1]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    report = {"fbx": fbx, "objects": len(meshes), "meshes": []}
    tris = 0
    for o in meshes:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
        report["meshes"].append({
            "name": o.name,
            "verts": len(o.data.vertices),
            "tris": len(o.data.loop_triangles),
            "has_custom_normals": bool(o.data.has_custom_normals),
            "max_loop_normal_angle_deg": round(max_loop_angle(o.data), 2),
            "uv_layers": [uv.name for uv in o.data.uv_layers],
            "materials": [s.material.name if s.material else None for s in o.material_slots],
            "dimensions": [round(v, 5) for v in o.dimensions],
            "location": [round(v, 5) for v in o.location],
        })
    report["total_tris"] = tris

    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    report["bbox_min"] = [round(v, 5) for v in mn]
    report["bbox_max"] = [round(v, 5) for v in mx]
    report["world_size"] = [round(mx[i] - mn[i], 5) for i in range(3)]

    center = (mn + mx) / 2
    span = max(mx - mn)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640

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
    cam_data.ortho_scale = span * 1.12
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = center + Vector((0, -1, 0)) * span * 2.0
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)

    Path(out_png).with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("FBX_VERIFY", json.dumps(report))


main()
