"""Render preview stills for the three ballast balls.

Usage:
    blender --background --factory-startup --python-exit-code 1 \
        --python render_previews.py -- <case_dir>

Geometry comes from build_ballast_balls.py by import, so the previews always
show the same meshes that get exported.
"""

import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

# Importing the builder module would otherwise leave a __pycache__ folder in
# the author directory.
sys.dont_write_bytecode = True

ENGINE_CANDIDATES = ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES')


def log(message):
    print("[preview] " + message)


def load_builder(case_dir):
    path = os.path.join(case_dir, "build_ballast_balls.py")
    spec = importlib.util.spec_from_file_location("ballast_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pick_engine(scene, samples=64):
    for name in ENGINE_CANDIDATES:
        try:
            scene.render.engine = name
            break
        except TypeError:
            continue
    try:
        scene.eevee.taa_render_samples = samples
    except Exception:
        pass
    return scene.render.engine


def add_area_light(name, location, energy, size, target=(0.0, 0.0, 0.02)):
    data = bpy.data.lights.new(name, type='AREA')
    data.energy = energy
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, Vector(target))
    return obj


def aim(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def studio(mats):
    scene = bpy.context.scene
    engine = pick_engine(scene)
    # Transparent background: the floor filled the whole frame on the first
    # passes and washed the part out. Asset previews stay readable on any
    # backdrop, matching the attachment icon standard.
    scene.render.film_transparent = True

    world = bpy.data.worlds.new("PreviewWorld")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (0.015, 0.016, 0.020, 1.0)
    background.inputs[1].default_value = 0.5

    # The subject is ~35 mm across and the lights sit ~0.4 m away, so wattage
    # has to stay small; 220 W blew the whole frame to white on the first pass.
    add_area_light("KeyLight", (0.30, -0.34, 0.42), 30.0, 0.5)
    add_area_light("FillLight", (-0.36, -0.26, 0.16), 6.0, 0.6)
    add_area_light("RimLight", (-0.10, 0.38, 0.30), 18.0, 0.5)
    log("engine=%s" % engine)
    return scene


def add_camera():
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 62.0
    cam_data.clip_start = 0.005
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def place_camera(cam, target, direction, radius, margin=1.22):
    target = Vector(target)
    direction = Vector(direction).normalized()
    sensor = cam.data.sensor_width
    fov = 2.0 * math.atan(sensor / (2.0 * cam.data.lens))
    distance = radius * margin / math.tan(fov / 2.0)
    cam.location = target + direction * distance
    aim(cam, target)


def render_to(path, width, height):
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    log("wrote %s" % os.path.basename(path))


def main():
    argv = sys.argv
    case_dir = argv[argv.index("--") + 1] if "--" in argv else os.path.dirname(os.path.abspath(__file__))
    preview_dir = os.path.join(case_dir, "preview")
    os.makedirs(preview_dir, exist_ok=True)
    builder = load_builder(case_dir)

    cam = None
    shots = (
        # file stem,        builder,              camera direction,   target,              radius, w,    h
        ("SM_Ballast_Hardened_Candidate_front", "build_hardened", (0.0, -1.0, 0.14), (0.0, 0.0, 0.021), 0.028, 1280, 1280),
        ("SM_Ballast_Hardened_Candidate_45", "build_hardened", (0.72, -1.0, 0.46), (0.0, 0.0, 0.021), 0.028, 1280, 1280),
        ("SM_Ballast_Rune_Candidate_front", "build_rune", (0.0, -1.0, 0.14), (0.0, 0.0, 0.021), 0.028, 1280, 1280),
        ("SM_Ballast_MagicOrb_Candidate_45", "build_magic_orb", (0.60, -0.85, 0.62), (0.0, 0.0, 0.024), 0.028, 1280, 1280),
        ("SM_Ballast_Hardened_Candidate_interface", "build_hardened", (0.55, -0.95, -0.22), (0.0, 0.0, 0.008), 0.026, 1280, 1280),
    )

    for file_stem, builder_name, direction, target, radius, width, height in shots:
        builder.reset_scene()
        mats = builder.make_materials()
        studio(mats)
        cam = add_camera()
        getattr(builder, builder_name)(mats)
        place_camera(cam, target, direction, radius)
        render_to(os.path.join(preview_dir, file_stem + ".png"), width, height)

    # Three-up comparison sheet.
    builder.reset_scene()
    mats = builder.make_materials()
    studio(mats)
    cam = add_camera()
    for index, builder_name in enumerate(("build_hardened", "build_rune", "build_magic_orb")):
        obj, _meta = getattr(builder, builder_name)(mats)
        obj.location = ((index - 1) * 0.055, 0.0, 0.0)
    place_camera(cam, (0.0, 0.0, 0.021), (0.30, -1.0, 0.34), 0.108, 1.10)
    render_to(os.path.join(preview_dir, "sheet_three_variants.png"), 1920, 800)


if __name__ == "__main__":
    main()
