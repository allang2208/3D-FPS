"""Render the magic orb ballast as blue glass based on the frost sword blade.

Usage:
    blender --background --factory-startup --python-exit-code 1 \
        --python render_magic_glass.py -- <case_dir>

The tint comes from the blade's measured base colour (see blade_material.json).
Two roughness values are shown: clear glass, and the blade's own sampled
roughness as a frosted alternative. The inner orb keeps its emissive core.
"""

import importlib.util
import json
import os
import sys

import bpy

sys.dont_write_bytecode = True


def log(message):
    print("[magicglass] " + message)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def enable_refraction(scene):
    """EEVEE needs raytracing on before transmission shows through."""
    try:
        scene.eevee.use_raytracing = True
    except Exception:
        pass
    try:
        scene.eevee.use_ssr = True
        scene.eevee.use_ssr_refraction = True
    except Exception:
        pass


def stage_for_glass(scene):
    """Glass needs something behind it to refract.

    The asset previews use a transparent film, which leaves transmission with
    nothing to bend; these shots keep an opaque dark stage instead.
    """
    scene.render.film_transparent = False
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        # A dark stage left the glass reading as opaque metal; it needs a lit
        # environment to transmit.
        background.inputs[0].default_value = (0.11, 0.13, 0.17, 1.0)
        background.inputs[1].default_value = 1.0


def boost_core(obj, strength=18.0):
    """Make the inner orb read through the glass instead of being washed out."""
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or "Core" not in mat.name:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        for socket_name in ("Emission Color", "Emission"):
            if socket_name in bsdf.inputs:
                bsdf.inputs[socket_name].default_value = (0.35, 0.75, 1.0, 1.0)
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = strength
        log("core %s emission strength=%.1f" % (mat.name, strength))


def glass_material(name, tint, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.0
    for socket_name in ("Transmission Weight", "Transmission"):
        if socket_name in bsdf.inputs:
            bsdf.inputs[socket_name].default_value = 1.0
            break
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.45
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 1.0
    # Blender 5.1 exposes use_raytrace_refraction + refraction_depth. The legacy
    # blend_method path stays unused: BLENDED breaks raytraced glass here.
    for attribute, value in (("use_raytrace_refraction", True),
                             ("use_screen_refraction", True),
                             ("refraction_depth", 0.05),
                             ("show_transparent_back", False),
                             ("use_backface_culling", False)):
        try:
            setattr(mat, attribute, value)
        except Exception:
            pass
    log("glass %s tint=(%.4f, %.4f, %.4f) roughness=%.3f" % (name, tint[0], tint[1], tint[2], roughness))
    return mat


def main():
    argv = sys.argv
    case_dir = argv[argv.index("--") + 1] if "--" in argv else os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(case_dir, "preview_magic_glass")
    os.makedirs(out_dir, exist_ok=True)

    builder = load_module("ballast_build", os.path.join(case_dir, "build_ballast_balls.py"))
    previews = load_module("ballast_preview", os.path.join(case_dir, "render_previews.py"))
    with open(os.path.join(case_dir, "blade_material.json"), encoding="utf-8") as handle:
        measured = json.load(handle)
    tint = measured["derived"]["base_color_linear"]
    blade_roughness = measured["derived"]["roughness_scalar"]
    clear_roughness = 0.08

    def scene_with_glass(roughness, suffix):
        builder.reset_scene()
        mats = builder.make_materials()
        previews.studio(mats)
        enable_refraction(bpy.context.scene)
        stage_for_glass(bpy.context.scene)
        cam = previews.add_camera()
        obj, _meta = builder.build_magic_orb(mats)
        boost_core(obj)
        glass = glass_material("M_Ballast_BladeGlass" + suffix, tint, roughness)
        # The housing and bezel become glass; the inner orb keeps its glow.
        core_material = obj.material_slots[-1].material if len(obj.material_slots) > 1 else None
        for slot in obj.material_slots:
            if slot.material is not core_material:
                slot.material = glass
        return cam, obj

    shots = (
        ("SM_Ballast_MagicOrb_glass_front", clear_roughness, "Clear", (0.0, -1.0, 0.20), (0.0, 0.0, 0.023), 0.028),
        ("SM_Ballast_MagicOrb_glass_45", clear_roughness, "Clear", (0.62, -0.88, 0.58), (0.0, 0.0, 0.024), 0.028),
    )
    for file_stem, roughness, suffix, direction, target, radius in shots:
        cam, _obj = scene_with_glass(roughness, suffix)
        previews.place_camera(cam, target, direction, radius)
        previews.render_to(os.path.join(out_dir, file_stem + ".png"), 1280, 1280)

    # Clear vs frosted comparison, both with the blade tint.
    builder.reset_scene()
    mats = builder.make_materials()
    previews.studio(mats)
    enable_refraction(bpy.context.scene)
    stage_for_glass(bpy.context.scene)
    cam = previews.add_camera()
    for index, (roughness, suffix) in enumerate(((clear_roughness, "Clear"), (blade_roughness, "Frosted"))):
        obj, _meta = builder.build_magic_orb(mats)
        boost_core(obj)
        core_material = obj.material_slots[-1].material if len(obj.material_slots) > 1 else None
        glass = glass_material("M_Ballast_BladeGlass" + suffix, tint, roughness)
        for slot in obj.material_slots:
            if slot.material is not core_material:
                slot.material = glass
        obj.location = ((index - 0.5) * 0.05, 0.0, 0.0)
    previews.place_camera(cam, (0.0, 0.0, 0.023), (0.30, -1.0, 0.40), 0.072, 1.10)
    previews.render_to(os.path.join(out_dir, "sheet_glass_clear_vs_frosted.png"), 1600, 900)

    # Transparency check: a bright bar behind the ball. If the shader really
    # transmits, the bar shows up broken and magnified through the sphere.
    cam, _obj = scene_with_glass(clear_roughness, "Clear")
    bar_material = bpy.data.materials.new("M_CheckBar")
    bar_material.use_nodes = True
    bar_bsdf = bar_material.node_tree.nodes.get("Principled BSDF")
    bar_bsdf.inputs["Base Color"].default_value = (0.85, 0.80, 0.35, 1.0)
    bar_bsdf.inputs["Roughness"].default_value = 0.4
    bpy.ops.mesh.primitive_cylinder_add(radius=0.004, depth=0.09, vertices=24,
                                        location=(0.0, 0.055, 0.02))
    bar = bpy.context.object
    bar.name = "TransparencyCheckBar"
    bar.data.materials.append(bar_material)
    previews.place_camera(cam, (0.0, 0.0, 0.021), (0.0, -1.0, 0.10), 0.030)
    previews.render_to(os.path.join(out_dir, "glass_transparency_check.png"), 1280, 1280)


if __name__ == "__main__":
    main()
