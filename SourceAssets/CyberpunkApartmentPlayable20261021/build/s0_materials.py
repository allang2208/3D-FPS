"""s0 — material patch pass.

Runs AFTER the MCP `material_create_pbr_from_textures` calls. It:
  * registers every texture material in cy_lib's MATS registry (key -> tile metres),
  * wires the emissive maps (holo panels, screens, neon grille, building facades),
  * tunes Normal Map node strength per surface type,
  * creates the flat (untextured) material set: glass, mirrors, neon tubes, plastics,
    rubbers, metals, fabrics, screens, holo volumetrics, wet puddles.
"""
from __future__ import annotations

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402

TEX = cy.TEX

TILES = {
    "concrete_floor": 3.0, "concrete_wall": 2.5, "concrete_ceiling": 3.0,
    "plaster": 2.0, "wood_floor": 2.0, "wood_dark": 0.8, "fabric": 0.55,
    "leather": 0.90, "metal_brushed": 0.6, "metal_rust": 1.2, "tile_bath": 1.2,
    "carpet": 0.5, "marble": 2.4, "rug": 3.2, "curtain": 1.4, "brick": 1.6,
    "holo_panel": 1.6, "tech_panel": 0.9, "circuit": 0.4, "screen_ui": 1.0,
    "asphalt_wet": 6.0, "deck_wet": 2.0, "diamond_plate": 0.5,
    "neon_grille": 0.8, "glass_smudge": 2.0, "wall_graffiti": 2.5,
    "facade_office": 8.0, "facade_hab": 6.0, "facade_mega": 12.0,
}

# how hard each surface reads its normal map
NSTR = {
    "concrete_floor": 1.0, "concrete_wall": 1.05, "concrete_ceiling": 0.9,
    "plaster": 0.35, "wood_floor": 1.6, "wood_dark": 1.0, "fabric": 0.55,
    "leather": 0.60, "metal_brushed": 0.55, "metal_rust": 1.4, "tile_bath": 1.1,
    "carpet": 1.2, "rug": 0.60, "marble": 0.35, "curtain": 0.50, "brick": 1.3,
    "tech_panel": 1.2, "circuit": 1.1, "diamond_plate": 1.0, "glass_smudge": 0.6,
    "deck_wet": 1.1, "asphalt_wet": 0.9, "wall_graffiti": 0.4,
    "facade_office": 0.7, "facade_hab": 0.7, "facade_mega": 0.6,
    "holo_panel": 0.3, "screen_ui": 0.0, "neon_grille": 0.0,
}

EMISSIVE = {
    "holo_panel": 6.0,
    "screen_ui": 3.2,
    "neon_grille": 9.0,
    # facades: the emissive map already covers ~11% of the surface, so the
    # strength has to stay low or the whole skyline turns into a grey wash
    "facade_office": 2.10,
    "facade_hab": 1.95,
    "facade_mega": 2.00,
}

# per-material tint applied to the emissive map: this is what gives the skyline
# its warm-window / cold-office / magenta-mega variety
EMISSIVE_TINT = {
    "facade_hab": (1.0, 0.66, 0.34),
    "facade_office": (0.42, 0.86, 1.0),
    "facade_mega": (1.0, 0.30, 0.78),
    "screen_ui": (0.72, 0.92, 1.0),
}


def nodes_of(m):
    return m.node_tree.nodes if m.use_nodes else []


def get_bsdf(m):
    for n in nodes_of(m):
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def add_emission_image(m, strength, tint=None):
    """Wire <key>_emi.png into the Principled emission input, optionally tinted."""
    img_path = os.path.join(TEX, f"{m.name}_emi.png")
    if not os.path.exists(img_path):
        return False
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.name = "Tex_Emission"
    tex.location = (-600, 600)
    img = bpy.data.images.load(img_path, check_existing=True)
    try:
        img.colorspace_settings.name = "sRGB"
    except Exception:
        pass
    tex.image = img
    bsdf = get_bsdf(m)
    if bsdf is None:
        return False
    src = tex.outputs["Color"]
    if tint is not None:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.location = (-300, 600)
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(src, mix.inputs[6])
        mix.inputs[7].default_value = (*tint, 1.0)
        src = mix.outputs[2]
    nt.links.new(src, bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    return True


def tune_normal(m, strength):
    for n in nodes_of(m):
        if n.type == "NORMAL_MAP":
            n.inputs["Strength"].default_value = strength
            return True
    return False


def make_glass(key, tint=(0.72, 0.86, 0.92), rough=0.03, tile=2.0, dirty=True):
    m = bpy.data.materials.get(key)
    if m is None:
        m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*tint, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.5
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 1.0
    elif "Transmission" in bsdf.inputs:
        bsdf.inputs["Transmission"].default_value = 1.0
    if dirty:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.location = (-600, -200)
        tex.image = bpy.data.images.load(os.path.join(TEX, "glass_smudge_rgh.png"), check_existing=True)
        try:
            tex.image.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "FLOAT"
        mix.location = (0, -150)
        # the smudge map must only *tint* the roughness, otherwise the pane turns frosted
        mix.inputs["Factor"].default_value = 0.06
        mix.inputs[2].default_value = rough
        nt.links.new(tex.outputs["Color"], mix.inputs[3])
        nt.links.new(mix.outputs[0], bsdf.inputs["Roughness"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (0, 150)
        nm.inputs["Strength"].default_value = 0.05
        nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
    cy.reg(key, m, tile)
    return m


def main() -> dict:
    reg = cy.MATS
    report = {"registered": 0, "emissive": [], "normal": [], "missing": []}

    for key, tile in TILES.items():
        m = bpy.data.materials.get(key)
        if m is None:
            report["missing"].append(key)
            continue
        cy.reg(key, m, tile)
        report["registered"] += 1
        if key in EMISSIVE and add_emission_image(m, EMISSIVE[key], EMISSIVE_TINT.get(key)):
            report["emissive"].append(key)
        if tune_normal(m, NSTR.get(key, 1.0)):
            report["normal"].append(key)

    # ---------------------------------------------------------------- glass
    make_glass("glass_window", tint=(0.80, 0.90, 0.96), rough=0.02, tile=2.0)
    make_glass("glass_balcony", tint=(0.55, 0.85, 0.92), rough=0.05, tile=1.5)
    make_glass("glass_shower", tint=(0.85, 0.92, 0.95), rough=0.06, tile=1.5)
    make_glass("glass_black", tint=(0.06, 0.07, 0.09), rough=0.04, tile=1.0, dirty=False)

    # ------------------------------------------------------------- mirrors
    cy.principled("mirror", (0.92, 0.93, 0.95), rough=0.02, metal=1.0, tile=1.0)

    # ---------------------------------------------------------------- neon
    NEON = {
        "neon_cyan": ((0.10, 0.95, 1.00), 14.0),
        "neon_magenta": ((1.00, 0.12, 0.62), 14.0),
        "neon_pink": ((1.00, 0.30, 0.55), 10.0),
        "neon_amber": ((1.00, 0.55, 0.10), 12.0),
        "neon_white": ((0.92, 0.97, 1.00), 16.0),
        "neon_red": ((1.00, 0.08, 0.08), 12.0),
        "neon_green": ((0.25, 1.00, 0.45), 10.0),
        "neon_violet": ((0.55, 0.20, 1.00), 12.0),
        "neon_blue": ((0.12, 0.35, 1.00), 12.0),
    }
    for k, (c, s) in NEON.items():
        cy.principled(k, (c[0] * 0.25, c[1] * 0.25, c[2] * 0.25), rough=0.3,
                      emit=c, emit_str=s, tile=1.0)

    # --------------------------------------------------------- flat PBR set
    FLAT = [
        ("metal_dark", (0.030, 0.032, 0.036), 0.42, 1.0),
        ("metal_steel", (0.42, 0.44, 0.47), 0.28, 1.0),
        ("metal_chrome", (0.85, 0.87, 0.90), 0.08, 1.0),
        ("metal_gold", (0.85, 0.62, 0.25), 0.22, 1.0),
        ("metal_copper", (0.72, 0.38, 0.22), 0.30, 1.0),
        ("metal_black", (0.015, 0.016, 0.018), 0.55, 0.7),
        ("paint_white", (0.62, 0.62, 0.60), 0.55, 0.0),
        ("paint_charcoal", (0.055, 0.057, 0.062), 0.62, 0.0),
        ("plastic_black", (0.020, 0.021, 0.024), 0.38, 0.0),
        ("plastic_white", (0.72, 0.72, 0.70), 0.34, 0.0),
        ("plastic_cream", (0.60, 0.56, 0.48), 0.40, 0.0),
        ("rubber", (0.014, 0.014, 0.016), 0.85, 0.0),
        ("ceramic_white", (0.86, 0.86, 0.84), 0.12, 0.0),
        ("wood_oak", (0.28, 0.18, 0.10), 0.55, 0.0),
        ("wood_walnut", (0.12, 0.070, 0.045), 0.50, 0.0),
        ("fabric_grey", (0.10, 0.105, 0.115), 0.85, 0.0),
        ("fabric_cream", (0.42, 0.40, 0.36), 0.88, 0.0),
        ("fabric_navy", (0.035, 0.045, 0.075), 0.86, 0.0),
        ("skin", (0.42, 0.27, 0.20), 0.60, 0.0),
        ("plant_green", (0.045, 0.16, 0.055), 0.55, 0.0),
        ("plant_green_dark", (0.020, 0.085, 0.030), 0.62, 0.0),
        ("plant_bamboo_stem", (0.20, 0.215, 0.075), 0.45, 0.0),
        ("stone_dark", (0.055, 0.052, 0.048), 0.72, 0.0),
        ("rope", (0.15, 0.12, 0.085), 0.88, 0.0),
        ("soil", (0.030, 0.024, 0.018), 0.95, 0.0),
        ("paper", (0.66, 0.64, 0.58), 0.80, 0.0),
        ("paper_dark", (0.18, 0.18, 0.19), 0.80, 0.0),
        ("water", (0.02, 0.05, 0.06), 0.02, 0.0),
        ("led_warm", (0.90, 0.62, 0.32), 0.5, 0.0),
        ("led_cool", (0.55, 0.75, 1.00), 0.5, 0.0),
        ("concrete_raw", (0.20, 0.198, 0.192), 0.80, 0.0),
        ("grout", (0.10, 0.10, 0.10), 0.85, 0.0),
        ("chrome_black", (0.030, 0.031, 0.034), 0.12, 1.0),
    ]
    for k, c, r, mt in FLAT:
        cy.principled(k, c, rough=r, metal=mt, tile=1.0)

    # the three plain fabric variants share the weave normal + roughness maps
    # from `fabric`, so bedding reads as cloth instead of smooth plastic
    _weave_fabrics()
    return _emissive_and_report()


def _weave_fabrics() -> None:
    """Rebuild fabric_cream / grey / navy on the shared weave maps."""
    src = bpy.data.materials.get("fabric")
    if src is None:
        return
    nrm = rgh = None
    for n in src.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            if "nrm" in n.image.name:
                nrm = n.image
            elif "rgh" in n.image.name:
                rgh = n.image
    if nrm is None:
        return
    variants = {
        "fabric_cream": ((0.560, 0.535, 0.480), 0.55, 0.88),
        "fabric_grey": ((0.135, 0.140, 0.152), 0.60, 0.86),
        "fabric_navy": ((0.048, 0.058, 0.095), 0.55, 0.84),
    }
    for key, (col, nstr, rough) in variants.items():
        m = bpy.data.materials.get(key) or bpy.data.materials.new(key)
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        out.location = (700, 0)
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (400, 0)
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        bsdf.inputs["Base Color"].default_value = (*col, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Specular IOR Level"].default_value = 0.32

        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = nrm
        tn.location = (-600, -260)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (-260, -260)
        nm.inputs["Strength"].default_value = nstr
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

        if rgh is not None:
            tr = nt.nodes.new("ShaderNodeTexImage")
            tr.image = rgh
            tr.location = (-600, 20)
            mr = nt.nodes.new("ShaderNodeMapRange")
            mr.location = (-260, 20)
            mr.inputs["To Min"].default_value = rough - 0.05
            mr.inputs["To Max"].default_value = rough + 0.05
            nt.links.new(tr.outputs["Color"], mr.inputs["Value"])
            nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

        cy.reg(key, m, 0.55)


def _emissive_and_report() -> dict:
    """Emission materials + the final report."""
    report: dict = {}
    # ------------------------------------------------- emissive flat set
    cy.emission("neon_strip_warm", (1.0, 0.72, 0.42), 12.0)
    cy.emission("neon_strip_cool", (0.45, 0.75, 1.0), 12.0)
    cy.emission("lamp_bulb", (1.0, 0.82, 0.60), 22.0)
    cy.emission("screen_glow", (0.35, 0.80, 1.0), 6.0)
    cy.emission("holo_cyan", (0.20, 0.95, 1.0), 9.0)
    cy.emission("holo_magenta", (1.0, 0.15, 0.75), 9.0)
    cy.emission("sign_box_warm", (1.0, 0.62, 0.28), 7.0)
    cy.emission("car_headlight", (1.0, 0.96, 0.90), 30.0)
    cy.emission("car_taillight", (1.0, 0.10, 0.06), 26.0)
    cy.emission("city_glow", (0.20, 0.35, 0.85), 4.0)
    cy.emission("traffic_red", (1.0, 0.05, 0.05), 18.0)
    cy.emission("traffic_green", (0.1, 1.0, 0.4), 18.0)

    # wet puddle (near-mirror dielectric, dark)
    cy.principled("puddle", (0.010, 0.014, 0.020), rough=0.03, metal=0.0, tile=1.0)

    report["materials_total"] = len(bpy.data.materials)
    report["registry"] = len(cy.MATS)
    return report


_result = main()