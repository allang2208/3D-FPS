"""Inspect the raw Diana OBJ in Blender and render orthogonal views.

The source OBJ is a photogrammetry export in Z-up world coordinates with the base
far from the origin (Z 24.17..43.75), so it is imported without axis rotation and
then only measured, never modified here.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <Diana_C.obj> <preview_dir>
"""
import sys
import math
import bpy
from mathutils import Vector

TILE = 640


def bounds(objs):
    pts = []
    for o in objs:
        for corner in o.bound_box:
            pts.append(o.matrix_world @ Vector(corner))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def main():
    argv = sys.argv
    args = argv[argv.index("--") + 1:]
    src, outdir = args[0], args[1]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=src, forward_axis='NEGATIVE_Y', up_axis='Z')

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    total_tris = 0
    print("=" * 72)
    print("SOURCE:", src)
    for o in meshes:
        o.data.calc_loop_triangles()
        total_tris += len(o.data.loop_triangles)
        print("object:", o.name, "verts:", len(o.data.vertices), "tris:", len(o.data.loop_triangles),
              "uv:", [uv.name for uv in o.data.uv_layers],
              "mats:", [s.material.name if s.material else None for s in o.material_slots])
    mn, mx = bounds(meshes)
    print("world bbox min:", tuple(round(v, 4) for v in mn))
    print("world bbox max:", tuple(round(v, 4) for v in mx))
    print("size (X,Y,Z):", tuple(round(mx[i] - mn[i], 4) for i in range(3)))
    print("TOTAL_TRIS:", total_tris)
    for img in bpy.data.images:
        print("image:", img.name, img.size[0], "x", img.size[1], "src:", img.filepath)
    print("=" * 72)

    # Render four orthogonal views so the facing direction can be judged visually.
    center = (mn + mx) / 2
    span = max(mx - mn)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.render.resolution_x = TILE
    scene.render.resolution_y = TILE
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("W")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.18, 0.19, 0.21, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

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

    views = {
        "front_looking_from_-Y": ((0, -1, 0), (math.radians(90), 0, 0)),
        "back_looking_from_+Y": ((0, 1, 0), (math.radians(90), 0, math.radians(180))),
        "side_looking_from_+X": ((1, 0, 0), (math.radians(90), 0, math.radians(90))),
        "side_looking_from_-X": ((-1, 0, 0), (math.radians(90), 0, math.radians(-90))),
    }
    dist = span * 2.0
    for name, (direction, rot) in views.items():
        cam.location = center + Vector(direction) * dist
        cam.rotation_euler = rot
        scene.render.filepath = "{}/{}".format(outdir, name)
        bpy.ops.render.render(write_still=True)
        print("rendered", name)


main()
