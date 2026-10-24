"""s4 - the three bedrooms.

MASTER  X 0.12..3.84   Y 0.12..5.40   (headboard on the west wall)
BED2    X 11.40..15.88 Y 0.12..5.40   (gaming room, headboard on the east wall)
BED3    X 11.40..15.88 Y 5.52..10.88  (studio / server room, window on X=16)
"""
from __future__ import annotations

import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402
import furn  # noqa: E402


def tri_count(cols):
    tris = 0
    for c in cols:
        cc = bpy.data.collections.get(c)
        if not cc:
            continue
        for o in cc.objects:
            if o.type == "MESH":
                o.data.calc_loop_triangles()
                tris += len(o.data.loop_triangles)
    return tris


def master(rng) -> None:
    C = "MASTER"
    cy.reset_col(C)
    mb = cy.MB("MST_room", C, bevel=0.003)
    # bed, headboard against the west wall
    mb.push((1.24, 2.60, 0))
    furn.bed(mb, w=1.80, l=2.10, pillows=2, key_duvet="fabric_cream", key_frame="wood_walnut")
    mb.pop()
    # nightstands + lamps
    for y in (1.32, 3.88):
        mb.push((0.44, y, 0))
        furn.nightstand(mb, 0.46, 0.40, 0.50)
        mb.pop()
        mb.push((0.44, y, 0.58))
        mb.cyl(0.085, 0.02, (0, 0, 0.01), seg=18, key="metal_gold")
        mb.cyl(0.012, 0.10, (0, 0, 0.06), seg=8, key="metal_gold")
        mb.cyl(0.11, 0.16, (0, 0, 0.19), seg=20, key="fabric_cream", r2=0.085)
        mb.cyl(0.10, 0.01, (0, 0, 0.115), seg=18, key="lamp_bulb")
        mb.pop()
    # wardrobe on the east wall
    mb.push((3.48, 2.65, 0), -math.pi / 2)
    furn.wardrobe(mb, w=3.00, h=2.42, d=0.62, doors=3)
    mb.pop()
    # dresser + mirror on the south wall
    mb.push((0.46, 4.65, 0), math.pi / 2)
    mb.box((1.30, 0.48, 0.80), (0, 0, 0.42), key="wood_walnut")
    mb.box((1.34, 0.52, 0.035), (0, 0, 0.845), key="metal_black")
    for i in range(3):
        mb.box((1.22, 0.02, 0.20), (0, -0.245, 0.22 + i * 0.24), key="wood_dark")
        mb.box((0.26, 0.014, 0.014), (0, -0.256, 0.22 + i * 0.24), key="metal_gold")
    mb.pop()
    # full-length mirror
    mb.push((3.55, 4.60, 0), -math.pi / 2)
    mb.box((0.66, 0.04, 1.85), (0, 0, 1.00), key="metal_black")
    mb.box((0.60, 0.006, 1.79), (0, -0.025, 1.00), key="mirror")
    mb.pop()
    # bench at the foot of the bed
    mb.push((2.62, 2.60, 0))
    mb.box((0.42, 1.60, 0.06), (0, 0, 0.42), key="leather")
    mb.box((0.40, 1.56, 0.03), (0, 0, 0.38), key="wood_walnut")
    for sy in (-1, 1):
        mb.box((0.30, 0.05, 0.38), (0, sy * 0.65, 0.19), key="metal_black")
    mb.pop()
    # rug
    mb.push((1.85, 2.60, 0))
    furn.rug(mb, 2.9, 3.5, thick=0.012, fringe=False)
    mb.pop()
    # plant + laundry basket + slippers
    mb.push((3.24, 0.72, 0))
    furn.plant_monstera(mb, random.Random(71), n=8, scale=0.80, pot_r=0.20, pot_h=0.30)
    mb.pop()
    mb.push((3.40, 1.35, 0))
    mb.cyl(0.24, 0.52, (0, 0, 0.26), seg=20, key="fabric_cream", r2=0.20)
    mb.pop()
    mb.push((2.20, 4.55, 0))
    furn.shoe_pair(mb, rng)
    mb.pop()
    # ceiling: pendant + LED cove
    mb.push((1.10, 2.60, 2.95))
    furn.pendant(mb, drop=1.05, r=0.22)
    mb.pop()
    furn.led_strip(mb, (0.20, 0.20, 2.88), (3.80, 0.20, 2.88), "neon_strip_warm", 0.025)
    # curtains
    mb.push((0.62, 0.22, 0))
    furn.curtain(mb, w=0.9, h=2.62, folds=5)
    mb.pop()
    mb.push((3.34, 0.22, 0))
    furn.curtain(mb, w=0.9, h=2.62, folds=5)
    mb.pop()
    mb.build()

    # clutter
    mb = cy.MB("MST_clutter", C, bevel=0.001)
    mb.push((0.44, 1.32, 0.58))
    furn.books_stack(mb, 2, rng, 0.20, 0.15)
    mb.pop()
    mb.push((0.44, 3.88, 0.58))
    furn.mug(mb, 0.035, 0.085)
    mb.pop()
    mb.push((0.44, 3.88, 0.58))
    mb.cyl(0.05, 0.06, (0.14, 0.05, 0.03), seg=14, key="plastic_white")
    mb.pop()
    mb.push((0.46, 4.65, 0.86))
    furn.bottle(mb, 0.20, 0.032, "glass_black", "metal_gold")
    mb.pop()
    mb.push((0.46, 4.65, 0.86))
    mb.box((0.10, 0.06, 0.03), (0.22, 0.02, 0.015), key="metal_gold")
    mb.pop()
    mb.build()

    # wall art above the bed (west wall)
    mb = cy.MB("MST_art", C, bevel=0.002)
    mb.push((0.14, 2.60, 1.35), math.pi / 2)
    mb.box((2.20, 0.03, 0.06), (0, 0, 0), key="neon_strip_warm")
    furn.picture_frame(mb, 0.90, 0.62, "metal_black", "holo_panel")
    mb.pop()
    mb.push((0.14, 2.60, 2.05), math.pi / 2)
    furn.picture_frame(mb, 0.60, 0.42, "metal_gold", "screen_ui")
    mb.pop()
    mb.build()

    # neon sign
    ob = cy.text_mesh("MST_sign", "DREAM", 0.26, (0.15, 2.60, 2.62),
                      rot=(math.pi / 2, 0, math.pi / 2), key="neon_violet", extrude=0.02,
                      col_name=C)


def bed2(rng) -> None:
    C = "BED2"
    cy.reset_col(C)
    mb = cy.MB("B2_room", C, bevel=0.003)
    # bed, headboard against the east wall
    mb.push((14.62, 3.10, 0), math.pi)
    furn.bed(mb, w=1.60, l=2.00, pillows=2, key_duvet="fabric_navy", key_frame="metal_black",
             headboard=1.05)
    mb.pop()
    for y in (1.95, 4.25):
        mb.push((15.55, y, 0))
        furn.nightstand(mb, 0.44, 0.40, 0.46)
        mb.pop()
        mb.push((15.55, y, 0.53))
        mb.cyl(0.075, 0.14, (0, 0, 0.07), seg=16, key="metal_black", r2=0.10)
        mb.cyl(0.07, 0.008, (0, 0, 0.005), seg=16, key="neon_cyan")
        mb.pop()
    # desk under the window, facing the view
    mb.push((13.30, 0.62, 0))
    furn.desk(mb, w=2.10, d=0.70, h=0.74, key_top="wood_dark")
    mb.pop()
    # monitors + pc + peripherals
    for i, x in enumerate((12.75, 13.30, 13.85)):
        mb.push((x, 0.42, 1.20), 0.0)
        furn.monitor(mb, 0.52, 0.30, tilt=0.06)
        mb.pop()
    mb.push((14.35, 0.55, 0.74))
    mb.box((0.24, 0.46, 0.44), (0, 0, 0.22), key="metal_black")
    mb.box((0.20, 0.005, 0.38), (0, -0.235, 0.24), key="neon_grille")
    mb.pop()
    mb.push((13.30, 0.78, 0.74))
    mb.box((0.46, 0.16, 0.03), (0, 0, 0.015), key="plastic_black")
    for i in range(14):
        mb.box((0.026, 0.026, 0.008), (-0.20 + i * 0.030, 0, 0.034), key="plastic_black")
    mb.box((0.07, 0.12, 0.035), (-0.31, 0.0, 0.017), key="plastic_black")
    mb.pop()
    # gaming chair
    mb.push((13.30, 1.35, 0), math.pi)
    mb.box((0.54, 0.52, 0.08), (0, 0, 0.46), key="leather")
    mb.box((0.54, 0.10, 0.78), (0, 0.24, 0.86), (-0.12, 0, 0), "leather")
    for sx in (-1, 1):
        mb.box((0.08, 0.10, 0.28), (sx * 0.32, 0.05, 0.62), key="plastic_black")
    mb.cyl(0.04, 0.40, (0, 0, 0.24), seg=10, key="metal_black")
    for i in range(5):
        a = i * 1.256
        mb.box((0.30, 0.06, 0.04), (math.cos(a) * 0.16, math.sin(a) * 0.16, 0.07),
               (0, 0, a), key="metal_black")
    mb.box((0.10, 0.02, 0.40), (0, 0.30, 1.10), (-0.12, 0, 0), "neon_magenta")
    mb.pop()
    # wardrobe on the south wall
    mb.push((14.00, 5.06, 0))
    furn.wardrobe(mb, w=2.70, h=2.40, d=0.62, doors=3)
    mb.pop()
    # shelf + record player
    mb.push((11.55, 2.60, 0), -math.pi / 2)
    mb.box((1.70, 0.34, 0.04), (0, 0, 0.86), key="wood_walnut")
    for i in range(3):
        mb.box((1.70, 0.34, 0.03), (0, 0, 0.30 + i * 0.28), key="wood_dark")
    for sx in (-1, 1):
        mb.box((0.04, 0.32, 0.86), (sx * 0.82, 0, 0.43), key="metal_black")
    mb.pop()
    # rug
    mb.push((13.60, 2.90, 0))
    furn.rug(mb, 3.0, 2.4, thick=0.012, fringe=False)
    mb.pop()
    # plant
    mb.push((12.06, 0.68, 0))
    furn.plant_monstera(mb, random.Random(83), n=7, scale=0.75, pot_r=0.19, pot_h=0.28)
    mb.pop()
    # ceiling
    mb.push((13.30, 2.90, 2.95))
    furn.track_light(mb, 2.0, 3)
    mb.pop()
    furn.led_strip(mb, (11.50, 5.30, 2.88), (15.80, 5.30, 2.88), "neon_magenta", 0.02)
    furn.led_strip(mb, (11.50, 0.25, 2.88), (15.80, 0.25, 2.88), "neon_cyan", 0.02)
    mb.build()

    # clutter
    mb = cy.MB("B2_clutter", C, bevel=0.001)
    mb.push((13.85, 0.62, 0.74))
    furn.can(mb, 0.033, 0.12, "neon_green")
    mb.pop()
    mb.push((13.55, 0.62, 0.74))
    furn.can(mb, 0.033, 0.12, "neon_magenta")
    mb.pop()
    mb.push((12.30, 0.62, 0.74))
    furn.takeout_container(mb)
    mb.pop()
    mb.push((15.55, 1.95, 0.51))
    furn.books_stack(mb, 3, rng, 0.22, 0.16)
    mb.pop()
    mb.push((15.55, 4.25, 0.51))
    furn.mug(mb, 0.04, 0.09)
    mb.pop()
    mb.push((11.55, 2.60, 1.12))
    mb.box((0.36, 0.36, 0.05), (0.3, 0, 0.025), key="plastic_black")
    mb.cyl(0.14, 0.012, (0.3, 0, 0.055), seg=22, key="metal_steel")
    mb.cyl(0.006, 0.16, (0.42, -0.12, 0.06), seg=6, key="metal_steel")
    mb.pop()
    # headphones on the desk
    mb.push((14.75, 0.62, 0.75))
    mb.add([(0.09, 0, 0), (0.05, 0, 0.16), (-0.05, 0, 0.16), (-0.09, 0, 0)], [(0, 1, 2, 3)],
           "plastic_black")
    for sx in (-1, 1):
        mb.cyl(0.05, 0.03, (sx * 0.09, 0, 0.0), rot=(0, math.pi / 2, 0), seg=14, key="plastic_black")
    mb.pop()
    # posters
    mb.push((11.42, 4.10, 1.55), -math.pi / 2)
    furn.poster(mb, 0.60, 0.86, "holo_panel")
    mb.pop()
    mb.push((11.42, 3.35, 1.62), -math.pi / 2)
    furn.poster(mb, 0.44, 0.60, "screen_ui")
    mb.pop()
    mb.build()

    ob = cy.text_mesh("B2_sign", "SYNTH", 0.22, (11.44, 1.55, 2.30),
                      rot=(math.pi / 2, 0, -math.pi / 2), key="neon_cyan", extrude=0.02,
                      col_name=C)


def bed3(rng) -> None:
    C = "BED3"
    cy.reset_col(C)
    mb = cy.MB("B3_room", C, bevel=0.003)
    # single bed against the back wall
    mb.push((12.30, 9.55, 0), -math.pi / 2)
    furn.bed(mb, w=1.00, l=2.00, pillows=1, key_duvet="fabric_grey", key_frame="metal_black",
             headboard=0.95)
    mb.pop()
    # desk under the east window
    mb.push((15.10, 8.20, 0), math.pi / 2)
    furn.desk(mb, w=2.20, d=0.70, h=0.74, key_top="wood_dark")
    mb.pop()
    for i, y in enumerate((7.65, 8.20, 8.75)):
        mb.push((15.30, y, 1.22), math.pi / 2)
        furn.monitor(mb, 0.52, 0.30, tilt=0.05)
        mb.pop()
    # synth keyboard on a stand
    mb.push((13.30, 6.20, 0), math.pi)
    mb.box((0.90, 0.26, 0.06), (0, 0, 0.72), (0.12, 0, 0), "plastic_black")
    for i in range(15):
        mb.box((0.05, 0.14, 0.012), (-0.42 + i * 0.06, -0.02, 0.755), (0.12, 0, 0), "plastic_white")
    for sx in (-1, 1):
        mb.box((0.04, 0.04, 0.72), (sx * 0.36, 0.05, 0.36), key="metal_black")
        mb.box((0.04, 0.30, 0.04), (sx * 0.36, -0.10, 0.03), key="metal_black")
    mb.box((0.36, 0.20, 0.04), (0.50, 0, 0.72), (0.12, 0, 0), "tech_panel")
    mb.pop()
    # server rack + desk chair
    mb.push((12.05, 6.10, 0), math.pi / 2)
    furn.server_rack(mb, 0.60, 0.70, 1.15)
    mb.pop()
    mb.push((14.30, 8.20, 0), -math.pi / 2)
    mb.box((0.50, 0.50, 0.08), (0, 0, 0.46), key="fabric_navy")
    mb.box((0.50, 0.08, 0.52), (0, 0.22, 0.75), (-0.1, 0, 0), "fabric_navy")
    mb.cyl(0.04, 0.42, (0, 0, 0.24), seg=10, key="metal_black")
    for i in range(5):
        a = i * 1.256
        mb.box((0.28, 0.05, 0.04), (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.07),
               (0, 0, a), key="metal_black")
    mb.pop()
    # shelving with boxes on the west wall
    mb.push((14.20, 10.64, 0), 0.0)
    furn.shelves(mb, w=1.0, h=2.05, d=0.34, n=4, rng=rng)
    mb.pop()
    mb.push((12.10, 10.60, 0))
    furn.box_stack(mb, 3, rng)
    mb.pop()
    # rug + plant
    mb.push((13.10, 8.00, 0))
    furn.rug(mb, 2.2, 2.0, thick=0.010, fringe=False)
    mb.pop()
    mb.push((12.00, 10.40, 0))
    furn.plant_snake(mb, random.Random(91))
    mb.pop()
    # lighting
    mb.push((13.40, 8.20, 2.95))
    furn.track_light(mb, 2.2, 3)
    mb.pop()
    furn.led_strip(mb, (11.50, 5.62, 2.88), (15.80, 5.62, 2.88), "neon_cyan", 0.02)
    # guitar leaning
    mb.push((15.60, 10.40, 0), -math.pi / 2 + 0.15)
    furn.guitar(mb)
    mb.pop()
    mb.build()

    mb = cy.MB("B3_clutter", C, bevel=0.001)
    mb.push((15.10, 8.20, 0.74))
    furn.mug(mb, 0.04, 0.09, "metal_steel")
    mb.pop()
    mb.push((14.80, 7.70, 0.74))
    furn.books_stack(mb, 2, rng, 0.20, 0.14)
    mb.pop()
    mb.push((15.10, 6.90, 0.74))
    furn.cable_coil(mb, 0.05, 3)
    mb.pop()
    mb.build()

    ob = cy.text_mesh("B3_sign", "NO SIGNAL", 0.20, (11.44, 9.55, 2.25),
                      rot=(math.pi / 2, 0, -math.pi / 2), key="neon_pink", extrude=0.02,
                      col_name=C)


def build() -> dict:
    rng = random.Random(555)
    master(rng)
    bed2(rng)
    bed3(rng)
    return {"objects": len(bpy.data.collections["MASTER"].objects)
            + len(bpy.data.collections["BED2"].objects)
            + len(bpy.data.collections["BED3"].objects),
            "tris": tri_count(["MASTER", "BED2", "BED3"])}


_result = build()
print(_result, flush=True)