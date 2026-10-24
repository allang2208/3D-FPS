"""s5 - bathrooms, foyer, utility alcove, corridor."""
from __future__ import annotations

import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402
import furn  # noqa: E402


def bath1(rng) -> None:
    C = "BATH1"
    cy.reset_col(C)
    mb = cy.MB("BA1_room", C, bevel=0.003)
    mb.push((3.78, 10.28, 0))
    furn.shower(mb, w=0.98, d=1.16, h=2.15)
    mb.pop()
    mb.push((3.14, 9.55, 0), math.pi / 2)
    furn.basin(mb, w=0.92, d=0.46, h=0.86)
    mb.pop()
    mb.push((3.14, 9.55, 1.55), math.pi / 2)
    furn.mirror(mb, w=0.86, h=0.92, z=0.0)
    mb.pop()
    mb.push((4.34, 9.15, 0), -math.pi / 2)
    furn.toilet(mb)
    mb.pop()
    # towel rail + towels
    mb.push((2.92, 8.35, 1.10))
    mb.cyl(0.014, 0.62, (0, 0, 0), rot=(0, math.pi / 2, 0), seg=8, key="metal_chrome")
    mb.box((0.60, 0.10, 0.46), (0, 0.06, -0.02), key="fabric_cream")
    mb.box((0.58, 0.04, 0.10), (0, 0.09, -0.24), key="fabric_cream")
    mb.pop()
    # floor mat
    mb.push((3.14, 9.35, 0.004))
    mb.box((0.80, 0.50, 0.012), (0, 0, 0), key="fabric_grey")
    mb.pop()
    mb.build()

    mb = cy.MB("BA1_clutter", C, bevel=0.001)
    for i in range(4):
        mb.push((3.05 + i * 0.12, 9.30, 0.88))
        mb.cyl(0.032, 0.16 + i * 0.03, (0, 0, 0.08), seg=10, key="plastic_white")
        mb.pop()
    mb.push((3.44, 9.62, 0.90))
    mb.cyl(0.05, 0.12, (0, 0, 0.06), seg=12, key="glass_window")
    mb.cyl(0.03, 0.05, (0, 0, 0.145), seg=10, key="metal_chrome")
    mb.pop()
    mb.push((4.40, 10.55, 0))
    furn.plant_snake(mb, random.Random(101))
    mb.pop()
    mb.build()


def bath2(rng) -> None:
    C = "BATH2"
    cy.reset_col(C)
    mb = cy.MB("BA2_room", C, bevel=0.003)
    mb.push((1.42, 10.40, 0))
    furn.bathtub(mb, w=1.68, d=0.78, h=0.56)
    mb.pop()
    mb.push((0.44, 8.95, 0), math.pi / 2)
    furn.basin(mb, w=0.92, d=0.46, h=0.86)
    mb.pop()
    mb.push((0.44, 8.95, 1.55), math.pi / 2)
    furn.mirror(mb, w=0.86, h=0.92, z=0.0)
    mb.pop()
    mb.push((2.36, 8.66, 0), -math.pi / 2)
    furn.toilet(mb)
    mb.pop()
    # towel ladder + framed art
    mb.push((2.60, 9.30, 1.05))
    for i in range(3):
        mb.cyl(0.012, 0.50, (0, 0, i * 0.22), rot=(math.pi / 2, 0, 0), seg=8, key="metal_black")
        mb.box((0.06, 0.44, 0.10), (0, 0, i * 0.22 + 0.04), key="fabric_cream")
    mb.pop()
    mb.push((1.40, 8.24, 1.60), 0)
    furn.picture_frame(mb, 0.50, 0.66, "metal_black", "holo_panel")
    mb.pop()
    mb.push((1.42, 9.90, 0.004))
    mb.box((1.10, 0.60, 0.012), (0, 0, 0), key="fabric_grey")
    mb.pop()
    mb.build()

    mb = cy.MB("BA2_clutter", C, bevel=0.001)
    mb.push((0.28, 10.60, 0.58))
    furn.bottle(mb, 0.20, 0.03, "glass_window", "plastic_white")
    mb.pop()
    mb.push((0.40, 10.60, 0.58))
    furn.bottle(mb, 0.16, 0.03, "glass_window", "neon_magenta")
    mb.pop()
    mb.push((2.34, 10.52, 0))
    furn.plant_monstera(mb, random.Random(103), n=5, scale=0.55, pot_r=0.14, pot_h=0.22)
    mb.pop()
    mb.build()


def alcove(rng) -> None:
    C = "UTILITY"
    cy.reset_col(C)
    mb = cy.MB("UTL_room", C, bevel=0.003)
    mb.push((3.18, 7.30, 0), math.pi / 2)
    furn.washer(mb, 0.60, 0.60, 0.84)
    mb.pop()
    mb.push((3.18, 7.30, 0.86), math.pi / 2)
    furn.washer(mb, 0.60, 0.60, 0.84)
    mb.pop()
    # shelf above + detergent
    mb.push((3.60, 7.30, 1.80), math.pi / 2)
    mb.box((1.30, 0.40, 0.03), (0, 0, 0), key="wood_dark")
    mb.box((1.30, 0.02, 0.10), (0, 0.19, 0.06), key="metal_black")
    mb.pop()
    # broom + bucket
    mb.push((4.45, 7.60, 0))
    mb.cyl(0.016, 1.30, (0, 0, 0.65), (0.05, 0.03, 0), seg=8, key="wood_oak")
    mb.box((0.10, 0.30, 0.04), (0, 0, 0.10), key="plastic_black")
    mb.pop()
    mb.push((4.40, 7.10, 0))
    mb.cyl(0.15, 0.30, (0, 0, 0.15), seg=18, key="plastic_cream", r2=0.17)
    mb.pop()
    mb.build()

    mb = cy.MB("UTL_clutter", C, bevel=0.001)
    for i in range(4):
        mb.push((3.20 + i * 0.22, 7.30, 1.81))
        mb.cyl(0.07, 0.22, (0, 0, 0.11), seg=12, key=["plastic_white", "neon_magenta",
                                                       "neon_cyan", "plastic_cream"][i])
        mb.pop()
    mb.push((3.90, 7.05, 0))
    furn.box_stack(mb, 2, rng)
    mb.pop()
    mb.build()


def foyer(rng) -> None:
    C = "FOYER"
    cy.reset_col(C)
    mb = cy.MB("FOY_room", C, bevel=0.003)
    # shoe cabinet against the east wall
    mb.push((11.02, 9.35, 0), -math.pi / 2)
    mb.box((1.60, 0.38, 1.10), (0, 0, 0.55), key="wood_dark")
    for i in range(4):
        mb.box((1.56, 0.02, 0.24), (0, -0.195, 0.16 + i * 0.26), key="wood_walnut")
        mb.box((0.24, 0.012, 0.012), (0, -0.208, 0.16 + i * 0.26), key="metal_gold")
    mb.box((1.62, 0.40, 0.03), (0, 0, 1.115), key="marble")
    mb.pop()
    # console on the west wall + mirror
    mb.push((9.02, 9.45, 0), math.pi / 2)
    furn.console_table(mb, w=1.60, d=0.34, h=0.80)
    mb.pop()
    mb.push((8.80, 9.45, 1.55), math.pi / 2)
    mb.box((1.30, 0.04, 1.05), (0, 0, 0), key="metal_gold")
    mb.box((1.22, 0.006, 0.97), (0, -0.024, 0), key="mirror")
    mb.pop()
    # coat rack
    mb.push((10.95, 10.20, 0))
    mb.cyl(0.20, 0.03, (0, 0, 0.015), seg=20, key="metal_black")
    mb.cyl(0.016, 1.80, (0, 0, 0.90), seg=10, key="metal_black")
    for i in range(4):
        a = i * 1.57 + 0.4
        mb.box((0.03, 0.20, 0.03), (math.cos(a) * 0.10, math.sin(a) * 0.10, 1.60),
               (0, 0, a), key="metal_black")
    mb.box((0.34, 0.16, 0.72), (0.02, 0.10, 1.15), (0, 0, 0.1), key="fabric_navy")
    mb.box((0.30, 0.14, 0.55), (-0.12, 0.05, 1.00), (0, 0, -0.08), key="leather")
    mb.pop()
    # door mat + parcels + shoes
    mb.push((9.92, 10.55, 0.004))
    mb.box((1.10, 0.62, 0.014), (0, 0, 0), (0, 0, 0.04), key="fabric_grey")
    mb.pop()
    mb.push((8.95, 10.35, 0))
    furn.box_stack(mb, 3, rng)
    mb.pop()
    mb.push((9.00, 7.05, 0))
    furn.shoe_pair(mb, rng)
    mb.pop()
    mb.push((9.00, 7.35, 0))
    furn.shoe_pair(mb, rng)
    mb.pop()
    # umbrella stand
    mb.push((8.92, 8.10, 0))
    furn.umbrella_stand(mb)
    mb.pop()
    # keypad + intercom by the door
    mb.push((11.00, 10.86, 1.45))
    mb.box((0.11, 0.05, 0.17), (0, 0, 0), key="tech_panel")
    mb.box((0.07, 0.006, 0.05), (0, -0.028, 0.04), key="screen_ui")
    mb.pop()
    mb.build()

    mb = cy.MB("FOY_clutter", C, bevel=0.001)
    mb.push((9.02, 9.45, 0.80))
    furn.books_stack(mb, 2, rng, 0.20, 0.14)
    mb.pop()
    mb.push((9.35, 9.45, 0.80))
    mb.cyl(0.10, 0.025, (0, 0, 0.012), seg=18, key="metal_gold")
    mb.pop()
    mb.push((11.02, 9.35, 1.13))
    furn.plant_snake(mb, random.Random(107))
    mb.pop()
    mb.build()

    ob = cy.text_mesh("FOY_sign", "48F", 0.34, (11.26, 9.95, 1.85),
                      rot=(math.pi / 2, 0, -math.pi / 2), key="neon_amber", extrude=0.03,
                      col_name=C)


def corridor(rng) -> None:
    C = "CORRIDOR"
    cy.reset_col(C)
    mb = cy.MB("COR_room", C, bevel=0.002)
    mb.push((5.70, 6.12, 0))
    furn.rug(mb, 9.6, 0.86, thick=0.010, fringe=False)
    mb.pop()
    # frames along the corridor
    for i, x in enumerate((1.20, 3.40, 5.60, 7.80, 10.00)):
        mb.push((x, 5.53, 1.42), 0)
        furn.picture_frame(mb, 0.34 if i % 2 else 0.46, 0.44 if i % 2 else 0.58,
                           "metal_black", "holo_panel" if i % 2 else "screen_ui")
        mb.pop()
    # runner LED + ceiling linear light
    furn.led_strip(mb, (0.30, 6.12, 2.90), (11.10, 6.12, 2.90), "neon_strip_cool", 0.035)
    # radiator on the south wall
    mb.push((8.60, 6.66, 0.45))
    for i in range(11):
        mb.box((0.10, 0.09, 0.55), (-0.50 + i * 0.10, 0, 0), key="metal_white")
    mb.box((1.15, 0.03, 0.03), (0, -0.07, 0.28), key="metal_steel")
    mb.pop()
    mb.push((0.60, 6.50, 0))
    furn.plant_bamboo(mb, random.Random(109), n=4, scale=0.45)
    mb.pop()
    mb.build()

    mb = cy.MB("COR_clutter", C, bevel=0.001)
    # delivery bot parked against the wall
    mb.push((10.70, 6.50, 0))
    mb.box((0.46, 0.40, 0.34), (0, 0, 0.20), key="plastic_white")
    mb.box((0.38, 0.32, 0.06), (0, 0, 0.42), key="metal_black")
    mb.box((0.22, 0.02, 0.10), (0, -0.20, 0.24), key="screen_ui")
    for sx in (-1, 1):
        mb.cyl(0.075, 0.05, (sx * 0.18, 0, 0.055), rot=(math.pi / 2, 0, 0), seg=14, key="rubber")
    mb.cyl(0.02, 0.14, (0, 0, 0.52), seg=8, key="metal_steel")
    mb.sphere(0.025, (0, 0, 0.60), seg=8, rings=6, key="neon_cyan")
    mb.pop()
    # wall-mounted floor plan sign
    mb.push((2.60, 6.70, 1.45), 0)
    mb.box((0.70, 0.03, 0.50), (0, 0, 0), key="tech_panel")
    mb.pop()
    mb.build()


def build() -> dict:
    rng = random.Random(909)
    bath1(rng)
    bath2(rng)
    alcove(rng)
    foyer(rng)
    corridor(rng)
    cols = ["BATH1", "BATH2", "UTILITY", "FOYER", "CORRIDOR"]
    tris = 0
    objs = 0
    for c in cols:
        cc = bpy.data.collections.get(c)
        if not cc:
            continue
        objs += len(cc.objects)
        for o in cc.objects:
            if o.type == "MESH":
                o.data.calc_loop_triangles()
                tris += len(o.data.loop_triangles)
    return {"objects": objs, "tris": tris}


_result = build()
print(_result, flush=True)