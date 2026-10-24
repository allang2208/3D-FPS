"""s8 — lighting rig, world, Cycles render settings.

Night scene: cool city spill through the glazing, warm practicals inside,
neon accents (magenta/cyan) on the balcony and in the living room.
"""
from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402


def world_nodes() -> bpy.types.World:
    w = bpy.data.worlds.get("CP_Night") or bpy.data.worlds.new("CP_Night")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (600, 0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (350, 0)
    bg.inputs["Strength"].default_value = 1.0

    # vertical gradient: deep indigo overhead -> magenta haze at the horizon
    texco = nt.nodes.new("ShaderNodeTexCoord")
    texco.location = (-900, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-700, 0)
    mapr = nt.nodes.new("ShaderNodeMapRange")
    mapr.location = (-500, 0)
    mapr.inputs["From Min"].default_value = -0.15
    mapr.inputs["From Max"].default_value = 0.55
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-250, 0)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.050, 0.030, 0.062, 1.0)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (0.014, 0.020, 0.048, 1.0)
    e2 = ramp.color_ramp.elements.new(0.85)
    e2.color = (0.003, 0.006, 0.018, 1.0)
    nt.links.new(texco.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # faint cloud layer lit from below by the city
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-900, -350)
    noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.62
    nramp = nt.nodes.new("ShaderNodeValToRGB")
    nramp.location = (-650, -350)
    nramp.color_ramp.elements[0].position = 0.42
    nramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    nramp.color_ramp.elements[1].position = 0.72
    nramp.color_ramp.elements[1].color = (0.10, 0.045, 0.11, 1.0)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "ADD"
    mix.location = (100, 0)
    mix.inputs["Factor"].default_value = 0.55
    nt.links.new(noise.outputs["Fac"], nramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs[6])
    nt.links.new(nramp.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bg.inputs["Color"])

    bpy.context.scene.world = w
    return w


def add_light(name, kind, loc, energy, color, size=1.0, size_y=None, coll="LIGHTS",
              rot=None, spread=None, shape="RECTANGLE"):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.shape = shape
        ld.size = size
        if size_y:
            ld.size_y = size_y
        if spread is not None:
            ld.spread = spread
    if kind in ("SPOT", "POINT"):
        if kind == "SPOT":
            ld.spot_size = math.radians(spread or 60)
            ld.spot_blend = 0.35
    if rot is not None and kind == "AREA" and hasattr(ld, "spread"):
        ld.spread = math.radians(180)
    ob = bpy.data.objects.new(name, ld)
    cy.col(coll).objects.link(ob)
    ob.location = loc
    # never let the emitter itself be visible to the camera: the exterior spill
    # lights would otherwise fill the window with a white card
    for attr in ("visible_camera", "visible_shadow"):
        if hasattr(ob, attr):
            try:
                setattr(ob, attr, False if attr == "visible_camera" else True)
            except Exception:
                pass
    if rot is not None:
        ob.rotation_euler = rot
    return ob


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def build() -> dict:
    cy.reset_col("LIGHTS")
    world_nodes()
    scn = bpy.context.scene
    S = "LIGHTS"

    # ------------------------------------------------------- city spill
    # distant, very broad sources standing in for the glow of the city itself:
    # far enough that they do not blow out the balcony deck
    l = add_light("L_city_cyan", "AREA", (7.6, -80.0, 40.0), 1250, (0.35, 0.72, 1.0), 80, 40, S)
    look_at(l, (7.6, -2.0, 1.0))
    l = add_light("L_city_magenta", "AREA", (-45.0, -60.0, 18.0), 950, (1.0, 0.22, 0.62), 40, 20, S)
    look_at(l, (3.0, -2.0, 1.0))
    l = add_light("L_city_amber", "AREA", (62.0, -50.0, 8.0), 380, (1.0, 0.62, 0.25), 40, 20, S)
    look_at(l, (11.0, -2.0, 1.0))

    # ------------------------------------------------------- living room
    l = add_light("L_living_key", "AREA", (7.4, 1.1, 2.80), 300.0, (1.0, 0.72, 0.45), 2.6, 1.1, S)
    l = add_light("L_living_fill", "AREA", (10.2, 3.6, 2.60), 120.0, (1.0, 0.80, 0.58), 1.6, 1.6, S)
    l = add_light("L_living_neon_mag", "AREA", (10.9, 0.35, 1.85), 160.0, (1.0, 0.14, 0.62), 0.8, 1.6, S)
    l = add_light("L_living_neon_cyan", "AREA", (4.35, 0.30, 2.20), 85.0, (0.20, 0.90, 1.0), 0.8, 1.2, S)
    l = add_light("L_screen", "AREA", (7.5, 4.9, 1.35), 64.0, (0.35, 0.75, 1.0), 1.2, 0.7, S)

    # ----------------------------------------------------------- kitchen
    l = add_light("L_kitchen_pendant", "AREA", (6.72, 9.10, 2.32), 152.0, (1.0, 0.78, 0.50), 1.1, 1.1, S)
    l = add_light("L_kitchen_uc1", "AREA", (6.30, 10.62, 1.52), 44.8, (1.0, 0.85, 0.62), 1.2, 0.4, S)
    l = add_light("L_kitchen_uc2", "AREA", (7.60, 10.62, 1.52), 44.8, (1.0, 0.85, 0.62), 1.2, 0.4, S)

    # ---------------------------------------------------------- corridor
    # downlights plus low wall washes: a 1.2 m wide tunnel only lit from the
    # ceiling reads as a black slot, so the walls get their own grazing light
    for i, x in enumerate((1.5, 4.2, 6.9, 9.6)):
        add_light(f"L_corr_{i}", "SPOT", (x, 6.12, 2.84), 38, (1.0, 0.80, 0.58),
                  spread=110, rot=(0, 0, 0))
    for i, x in enumerate((0.9, 3.6, 6.3, 9.0)):
        add_light(f"L_corr_w{i}", "AREA", (x, 5.62, 1.95), 15, (1.0, 0.74, 0.50),
                  1.4, 0.35, S, rot=(math.radians(90), 0, 0))
        add_light(f"L_corr_e{i}", "AREA", (x, 6.62, 1.95), 15, (0.55, 0.80, 1.0),
                  1.4, 0.35, S, rot=(math.radians(-90), 0, 0))
    # ---------------------------------------------------------- foyer
    l = add_light("L_foyer", "SPOT", (10.0, 8.80, 2.84), 120, (1.0, 0.78, 0.55), spread=115)
    add_light("L_foyer_dl", "AREA", (9.60, 9.90, 2.78), 70, (1.0, 0.80, 0.58), 1.0, 1.0, S)
    add_light("L_foyer_wash", "AREA", (10.80, 9.60, 2.10), 45, (1.0, 0.35, 0.65),
              1.6, 0.4, S, rot=(0, math.radians(-90), 0))
    add_light("L_foyer_door", "AREA", (10.55, 10.55, 1.90), 30, (0.60, 0.85, 1.0),
              0.9, 1.6, S, rot=(math.radians(-90), 0, 0))

    # ---------------------------------------------------------- bedrooms
    l = add_light("L_master_lamp", "POINT", (0.55, 0.60, 1.35), 55, (1.0, 0.62, 0.34))
    l = add_light("L_master_ceiling", "AREA", (2.0, 2.6, 2.86), 150, (1.0, 0.72, 0.48), 1.8, 1.8, S)
    add_light("L_master_fill", "AREA", (3.40, 4.60, 2.30), 55, (1.0, 0.78, 0.55), 1.2, 1.2, S)
    add_light("L_master_wash", "AREA", (0.50, 2.60, 2.10), 40, (0.45, 0.75, 1.0),
              1.8, 0.4, S, rot=(0, math.radians(90), 0))
    l = add_light("L_bed2_lamp", "POINT", (12.15, 0.75, 1.30), 50, (0.55, 0.75, 1.0))
    l = add_light("L_bed2_ceiling", "AREA", (13.6, 2.8, 2.86), 120, (0.85, 0.70, 1.0), 1.7, 1.7, S)
    add_light("L_bed2_fill", "AREA", (15.40, 1.20, 2.20), 45, (1.0, 0.55, 0.75), 1.2, 1.2, S)
    l = add_light("L_bed3_desk", "AREA", (14.2, 7.4, 1.45), 62, (0.35, 0.85, 1.0), 1.0, 0.6, S)
    l = add_light("L_bed3_ceiling", "AREA", (13.6, 8.8, 2.86), 100, (1.0, 0.75, 0.52), 1.8, 1.8, S)
    add_light("L_bed3_fill", "AREA", (12.10, 10.20, 2.25), 42, (0.55, 0.85, 1.0), 1.2, 1.2, S)

    # -------------------------------------------------------------- baths
    add_light("L_bath1", "AREA", (3.76, 9.5, 2.80), 60.8, (0.90, 0.95, 1.0), 1.2, 1.2, S)
    add_light("L_bath2", "AREA", (1.4, 9.5, 2.80), 54.4, (0.90, 0.95, 1.0), 1.2, 1.2, S)

    # ------------------------------------------------------------ balcony
    l = add_light("L_balcony_neon", "AREA", (5.6, -2.70, 1.9), 130.0, (1.0, 0.16, 0.66), 2.0, 0.5, S)
    l = add_light("L_balcony_cyan", "AREA", (9.6, -2.70, 1.4), 120.0, (0.20, 0.95, 1.0), 1.6, 0.4, S)
    for i, x in enumerate((4.8, 6.4, 8.0, 9.6)):
        add_light(f"L_balcony_dl{i}", "SPOT", (x, -2.20, 2.94), 22, (1.0, 0.70, 0.42), spread=110)

    # ---------------------------------------------------------- render cfg
    scn.render.engine = "CYCLES"
    scn.cycles.device = "GPU"
    scn.cycles.samples = 160
    scn.cycles.preview_samples = 24
    scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 8
    scn.cycles.diffuse_bounces = 4
    scn.cycles.glossy_bounces = 4
    scn.cycles.transmission_bounces = 8
    scn.cycles.transparent_max_bounces = 8
    scn.cycles.volume_bounces = 2
    scn.cycles.sample_clamp_indirect = 8.0
    scn.cycles.blur_glossy = 1.0
    scn.cycles.use_fast_gi = False
    scn.render.film_transparent = False
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Punchy"
    scn.view_settings.exposure = 0.0
    scn.render.resolution_x = 1600
    scn.render.resolution_y = 900
    scn.render.resolution_percentage = 100
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.fps = 24

    # GPU devices
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type != "CPU"
        scn.cycles.device = "GPU"
        dev = [d.name for d in prefs.devices if d.use]
    except Exception as exc:  # noqa: BLE001
        scn.cycles.device = "CPU"
        dev = [f"cpu-fallback:{exc}"]

    lights = [o for o in bpy.data.objects if o.type == "LIGHT"]
    return {"lights": len(lights), "devices": dev,
            "engine": scn.render.engine, "world": scn.world.name if scn.world else None,
            "view_transform": scn.view_settings.view_transform}


_result = build()
print(_result, flush=True)