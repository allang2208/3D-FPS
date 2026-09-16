"""Render the hardened and rune ballast balls with the frost sword pommel material.

Usage:
    blender --background --factory-startup --python-exit-code 1 \
        --python render_pommel_material.py -- <case_dir>

Two looks are produced:

  preview_pommel/    flat PBR derived from the pommel's measured texture means
  preview_pommel/*_textured.png   the same four textures applied straight to
                                  the ball, i.e. M_FrostCrystalSword itself

Everything is measured in pommel_material.json; see the case README.
"""

import importlib.util
import json
import os
import sys

import bpy

sys.dont_write_bytecode = True

TEX_DIR = ("D:/FPS3D/FPSGAME/SourceAssets/MeshyMelee20260915/Original/"
           "Meshy_AI_帮我生成一把半_0914033835_texture_fbx")
TEX_STEM = "Meshy_AI_帮我生成一把半_0914033835_texture"


def log(message):
    print("[pommelmat] " + message)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def srgb_to_linear(value):
    value = value / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def flat_material(name, measured):
    base = [srgb_to_linear(channel) for channel in measured["base_color_rgb"]]
    metallic = measured["metallic"] / 255.0
    roughness = measured["roughness"] / 255.0
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    log("flat material %s base_linear=%s metallic=%.3f roughness=%.3f" % (
        name, [round(value, 4) for value in base], metallic, roughness))
    return mat


def texture_material(name):
    """The literal M_FrostCrystalSword graph: four textures, no scalars."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    nodes, links = tree.nodes, tree.links
    bsdf = nodes.get("Principled BSDF")
    layout = (("BaseColor", "Color", "sRGB", "Base Color", None),
              ("Metallic", "Color", "Non-Color", "Metallic", "R"),
              ("Roughness", "Color", "Non-Color", "Roughness", "R"),
              ("Normal", "Color", "Non-Color", "Normal", None))
    y = -300
    for suffix, _, colorspace, target, channel in layout:
        path = os.path.join(TEX_DIR, "%s_%s.png" % (TEX_STEM, suffix)
                            if suffix != "BaseColor" else TEX_STEM + ".png")
        if not os.path.exists(path):
            raise SystemExit("missing texture: " + path)
        image = bpy.data.images.load(path)
        image.colorspace_settings.name = colorspace
        node = nodes.new("ShaderNodeTexImage")
        node.image = image
        node.location = (-500, y)
        y -= 300
        if target == "Normal":
            normal_map = nodes.new("ShaderNodeNormalMap")
            normal_map.location = (-200, y + 300)
            links.new(node.outputs["Color"], normal_map.inputs["Color"])
            links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
            continue
        if channel == "R":
            separate = nodes.new("ShaderNodeSeparateColor")
            separate.location = (-200, y + 300)
            links.new(node.outputs["Color"], separate.inputs["Color"])
            links.new(separate.outputs["Red"], bsdf.inputs[target])
        else:
            links.new(node.outputs["Color"], bsdf.inputs[target])
    log("texture material %s <- %s" % (name, TEX_STEM))
    return mat


def apply_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def main():
    argv = sys.argv
    case_dir = argv[argv.index("--") + 1] if "--" in argv else os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(case_dir, "preview_pommel")
    os.makedirs(out_dir, exist_ok=True)

    builder = load_module("ballast_build", os.path.join(case_dir, "build_ballast_balls.py"))
    previews = load_module("ballast_preview", os.path.join(case_dir, "render_previews.py"))
    with open(os.path.join(case_dir, "pommel_material.json"), encoding="utf-8") as handle:
        measured = json.load(handle)["sampled_mean_srgb_255"]

    shots = (
        ("SM_Ballast_Hardened_Candidate_pommel_front", "build_hardened", (0.0, -1.0, 0.14), (0.0, 0.0, 0.021), 0.028),
        ("SM_Ballast_Hardened_Candidate_pommel_45", "build_hardened", (0.72, -1.0, 0.46), (0.0, 0.0, 0.021), 0.028),
        ("SM_Ballast_Rune_Candidate_pommel_front", "build_rune", (0.0, -1.0, 0.14), (0.0, 0.0, 0.021), 0.028),
        ("SM_Ballast_Rune_Candidate_pommel_45", "build_rune", (0.72, -1.0, 0.46), (0.0, 0.0, 0.021), 0.028),
    )

    for file_stem, builder_name, direction, target, radius in shots:
        builder.reset_scene()
        mats = builder.make_materials()
        previews.studio(mats)
        cam = previews.add_camera()
        obj, _meta = getattr(builder, builder_name)(mats)
        apply_material(obj, flat_material("M_Ballast_FrostPommel", measured))
        previews.place_camera(cam, target, direction, radius)
        previews.render_to(os.path.join(out_dir, file_stem + ".png"), 1280, 1280)

    # Two-up sheet with the measured pommel material.
    builder.reset_scene()
    mats = builder.make_materials()
    previews.studio(mats)
    cam = previews.add_camera()
    flat = flat_material("M_Ballast_FrostPommel", measured)
    for index, builder_name in enumerate(("build_hardened", "build_rune")):
        obj, _meta = getattr(builder, builder_name)(mats)
        apply_material(obj, flat)
        obj.location = ((index - 0.5) * 0.05, 0.0, 0.0)
    previews.place_camera(cam, (0.0, 0.0, 0.021), (0.30, -1.0, 0.34), 0.072, 1.10)
    previews.render_to(os.path.join(out_dir, "sheet_two_pommel_material.png"), 1600, 900)

    # Same two balls with M_FrostCrystalSword's four textures, as a comparison.
    builder.reset_scene()
    mats = builder.make_materials()
    previews.studio(mats)
    cam = previews.add_camera()
    textured = texture_material("M_FrostCrystalSword_OnBall")
    for index, builder_name in enumerate(("build_hardened", "build_rune")):
        obj, _meta = getattr(builder, builder_name)(mats)
        apply_material(obj, textured)
        obj.location = ((index - 0.5) * 0.05, 0.0, 0.0)
    previews.place_camera(cam, (0.0, 0.0, 0.021), (0.30, -1.0, 0.34), 0.072, 1.10)
    previews.render_to(os.path.join(out_dir, "sheet_two_textured.png"), 1600, 900)


if __name__ == "__main__":
    main()
