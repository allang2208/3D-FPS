"""Zoomed views of the SVD receiver so the mechanical parts can be identified from pixels.

Renders three orthographic crops (right side receiver, magazine/trigger area, three-quarter)
plus a silhouette overlay of the shells whose bounding boxes look like a magazine, a
trigger or a charging handle - the labels come from measurement, the images confirm them.

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


def setup_scene(res=(1280, 720)):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = res
    world = bpy.data.worlds.new('W2')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.20, 0.21, 0.23, 1)
    sun = bpy.data.objects.new('Sun2', bpy.data.lights.new('Sun2', type='SUN'))
    sun.data.energy = 4.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(40))
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new('Cam2')
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new('Cam2', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def shoot(scene, cam, out, center, ortho, direction, rot):
    cam.data.ortho_scale = ortho
    cam.location = Vector(center) + Vector(direction) * 5.0
    cam.rotation_euler = rot
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    glb = case / 'Source' / 'svd_source.glb'
    outdir = case / 'Previews' / 'receiver'
    outdir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    bpy.context.view_layer.update()
    scene, cam = setup_scene()

    # right side of the receiver (source frame: muzzle +Y, up +Z, right +X)
    shoot(scene, cam, outdir / 'side_receiver.png', (0.0, -0.25, 0.12), 0.75,
          (1, 0, 0), (math.radians(90), 0, math.radians(90)))
    shoot(scene, cam, outdir / 'side_magazine.png', (0.0, -0.62, 0.05), 0.45,
          (1, 0, 0), (math.radians(90), 0, math.radians(90)))
    shoot(scene, cam, outdir / 'three_quarter.png', (0.0, -0.35, 0.10), 0.8,
          (0.8, -0.5, 0.3), (math.radians(70), 0, math.radians(58)))
    shoot(scene, cam, outdir / 'bottom.png', (0.0, -0.35, 0.0), 0.8,
          (0, 0, -1), (math.radians(180), 0, 0))
    print('RENDERS_DONE', outdir)


main()
