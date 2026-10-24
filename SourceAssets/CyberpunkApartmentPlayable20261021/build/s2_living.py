"""s2 -?living room (X 3.96..11.28, Y 0.12..5.40).

Media wall on the west wall, big sofa against the east wall, lounge chairs
turned toward the balcony glazing, neon signage, plants, clutter.
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

COL = "LIVING"


def sign(text, loc, rotz, size, key="neon_magenta", extrude=0.02):
    ob = cy.text_mesh(f"LIV_sign_{text[:8]}", text, size, loc,
                      rot=(math.pi / 2, 0, rotz), key=key, extrude=extrude, col_name=COL)
    return ob


def build() -> dict:
    cy.reset_col(COL)
    rng = random.Random(2024)

    # ---------------------------------------------------------------- rug
    mb = cy.MB("LIV_rug", COL, bevel=0.0)
    mb.push((8.25, 3.05, 0))
    furn.rug(mb, w=5.6, d=3.4, thick=0.014)
    mb.pop()
    mb.build()

    # ----------------------------------------------------------- furniture
    mb = cy.MB("LIV_furniture", COL, bevel=0.004)
    # sofa against the east wall, facing -X
    mb.push((10.52, 2.40, 0), -math.pi / 2)
    furn.sofa(mb, w=3.2, d=1.02, seats=3, key="fabric", arm_key="fabric", chaise=0.0)
    mb.pop()
    # chaise extension toward the window
    mb.push((9.10, 1.75, 0), 0.0)
    mb.box((1.35, 1.05, 0.32), (0, 0, 0.35), key="fabric")
    mb.box((1.28, 0.98, 0.14), (0, 0, 0.53), key="fabric")
    mb.pop()

    # armchairs facing the coffee table
    mb.push((6.05, 1.55, 0), math.pi + 0.18)
    furn.armchair(mb, 0.95, 0.95, key="leather")
    mb.pop()
    mb.push((6.05, 4.45, 0), -0.18)
    furn.armchair(mb, 0.95, 0.95, key="leather")
    mb.pop()

    # coffee table
    mb.push((8.25, 3.05, 0))
    furn.coffee_table(mb, w=1.75, d=0.98, h=0.36)
    mb.pop()

    # side table + floor lamp
    mb.push((10.95, 1.05, 0))
    furn.side_table(mb, 0.22, 0.52)
    mb.pop()
    mb.push((4.42, 4.92, 0))
    furn.floor_lamp(mb, h=1.52)
    mb.pop()

    # media console along the west wall
    mb.push((4.34, 2.95, 0), math.pi / 2)
    mb.box((2.90, 0.46, 0.42), (0, 0, 0.28), key="wood_walnut")
    mb.box((2.96, 0.50, 0.03), (0, 0, 0.505), key="marble")
    mb.box((2.80, 0.42, 0.05), (0, 0, 0.045), key="metal_black")
    for i in range(3):
        x = -0.95 + i * 0.95
        mb.box((0.90, 0.02, 0.34), (x, -0.235, 0.30), key="wood_dark")
        mb.box((0.24, 0.012, 0.012), (x, -0.248, 0.34), key="metal_gold")
    mb.box((2.70, 0.012, 0.008), (0, -0.22, 0.075), key="neon_strip_cool")
    # holo-TV on the wall above the console
    mb.push((0, 0, 0), 0)
    mb.box((2.46, 0.05, 1.38), (-0.02, 0.02, 1.86), key="metal_black")
    mb.box((2.40, 0.008, 1.32), (-0.02, -0.012, 1.86), key="screen_ui")
    mb.box((1.30, 0.26, 0.10), (-0.02, 0.10, 0.86), key="metal_black")
    mb.pop()

    mb.pop()  # close media-console frame before placing other furniture

    # bookshelf on the south wall (right of the living opening)
    mb.push((5.45, 5.30, 0), math.pi)
    furn.shelves(mb, w=1.7, h=1.95, d=0.32, n=4, rng=rng)
    mb.pop()

    # low bench under the window
    mb.push((10.55, 0.55, 0), 0)
    mb.box((1.60, 0.42, 0.38), (0, 0, 0.19), key="wood_walnut")
    mb.box((1.62, 0.44, 0.04), (0, 0, 0.40), key="leather")
    mb.pop()

    # arcade cabinet in the north-west corner
    mb.push((4.62, 0.78, 0), 0.35)
    furn.arcade_machine(mb)
    mb.pop()

    # speaker + subwoofer by the media wall
    mb.push((4.30, 1.30, 0), math.pi / 2)
    mb.box((0.24, 0.24, 1.05), (0, 0, 0.53), key="metal_black")
    for i in range(3):
        mb.cyl(0.055, 0.01, (0, -0.125, 0.35 + i * 0.28), rot=(math.pi / 2, 0, 0), seg=16,
               key="metal_dark")
    mb.pop()
    mb.push((4.36, 4.45, 0), math.pi / 2)
    mb.box((0.42, 0.42, 0.42), (0, 0, 0.21), key="metal_black")
    mb.cyl(0.15, 0.02, (0, -0.22, 0.20), rot=(math.pi / 2, 0, 0), seg=24, key="metal_dark")
    mb.pop()
    mb.build()

    # ------------------------------------------------------- ceiling kit
    mb = cy.MB("LIV_ceiling", COL, bevel=0.002)
    mb.push((7.4, 3.15, 2.95))
    furn.track_light(mb, length=4.6, n=4)
    mb.pop()
    mb.push((8.25, 3.05, 2.95))
    furn.pendant(mb, drop=1.55, r=0.19)
    mb.pop()
    # linear LED in the ceiling tray
    furn.led_strip(mb, (4.5, 0.55, 2.90), (10.8, 0.55, 2.90), "neon_strip_cool", 0.03)
    furn.led_strip(mb, (4.5, 4.15, 2.90), (10.8, 4.15, 2.90), "neon_strip_cool", 0.03)
    # curtain track
    mb.box((7.2, 0.05, 0.05), (7.62, 0.20, 2.86), key="metal_black")
    mb.build()

    # ----------------------------------------------------------- curtains
    mb = cy.MB("LIV_curtains", COL, bevel=0.0)
    mb.push((4.55, 0.24, 0))
    furn.curtain(mb, w=1.5, h=2.70, folds=7)
    mb.pop()
    mb.push((10.70, 0.24, 0))
    furn.curtain(mb, w=1.5, h=2.70, folds=7)
    mb.pop()
    mb.build()

    # ------------------------------------------------------------ plants
    mb = cy.MB("LIV_plants", COL, bevel=0.0)
    mb.push((5.16, 0.58, 0))
    furn.plant_monstera(mb, random.Random(41), n=11, scale=1.0, pot_r=0.26, pot_h=0.36)
    mb.pop()
    mb.push((10.80, 4.92, 0))
    furn.plant_snake(mb, random.Random(43))
    mb.pop()
    mb.push((7.90, 0.42, 0))
    furn.plant_bamboo(mb, random.Random(47), n=5, scale=0.55)
    mb.pop()
    # hanging planter by the media wall
    mb.push((4.30, 5.05, 2.62))
    furn.hanging_plant(mb, random.Random(51), drop=0.8)
    mb.pop()
    mb.build()

    # ------------------------------------------------------------- clutter
    mb = cy.MB("LIV_clutter", COL, bevel=0.001)
    # on the coffee table
    mb.push((8.10, 3.20, 0.36))
    furn.books_stack(mb, 3, rng)
    mb.pop()
    mb.push((8.62, 2.86, 0.36))
    furn.mug(mb, key="ceramic_white")
    mb.pop()
    mb.push((8.62, 2.86, 0.36))
    furn.mug(mb, key="ceramic_white")
    mb.pop()
    mb.push((7.72, 3.33, 0.40))
    furn.vr_headset(mb)
    mb.pop()
    # laptop on the chaise
    mb.push((9.15, 1.80, 0.60))
    mb.box((0.34, 0.24, 0.015), (0, 0, 0.008), key="metal_steel")
    mb.box((0.34, 0.012, 0.24), (0, 0.11, 0.12), (-0.22, 0, 0), key="metal_steel")
    mb.box((0.32, 0.006, 0.22), (0, 0.095, 0.12), (-0.22, 0, 0), key="screen_ui")
    mb.pop()
    # console: game pads, console box, remote
    mb.push((4.34, 2.10, 0.52), math.pi / 2)
    mb.box((0.16, 0.10, 0.05), (-0.4, 0, 0.03), key="plastic_black")
    mb.box((0.30, 0.24, 0.04), (0.45, 0, 0.02), key="plastic_black")
    mb.box((0.05, 0.16, 0.02), (0.0, 0, 0.01), key="plastic_black")
    mb.pop()
    # books + magazines on the shelves / bench
    mb.push((10.30, 0.55, 0.42))
    furn.books_stack(mb, 4, rng)
    mb.pop()
    mb.push((9.95, 0.55, 0.42))
    furn.bottle(mb, 0.24, 0.035, "glass_black")
    mb.pop()
    # floor clutter: power strip, cables
    mb.push((4.55, 2.95, 0.02))
    mb.box((0.30, 0.07, 0.05), (0, 0, 0.025), key="plastic_white")
    for i in range(5):
        mb.cyl(0.008, 0.005, (-0.12 + i * 0.06, -0.036, 0.025), rot=(math.pi / 2, 0, 0),
               seg=8, key="plastic_black")
    mb.pop()
    mb.build()

    # ------------------------------------------------------------- cables
    mb = cy.MB("LIV_cables", COL, bevel=0.0)
    mb.tube(cy.catenary((4.36, 2.60, 0.06), (4.36, 3.40, 0.06), 0.10, 10), 0.008, "plastic_black")
    mb.tube(cy.catenary((4.40, 1.10, 0.50), (4.40, 2.10, 0.20), 0.18, 10), 0.006, "plastic_black")
    mb.tube(cy.catenary((10.62, 0.30, 0.62), (10.62, 1.20, 0.10), 0.22, 10), 0.006, "plastic_black")
    mb.build()

    # -------------------------------------------------------------- wall art
    mb = cy.MB("LIV_art", COL, bevel=0.002)
    mb.push((11.30, 2.35, 1.35), -math.pi / 2)
    furn.picture_frame(mb, 0.56, 0.72, "metal_black", "holo_panel")
    mb.pop()
    mb.push((11.30, 3.15, 1.45), -math.pi / 2)
    furn.picture_frame(mb, 0.44, 0.56, "metal_gold", "screen_ui")
    mb.pop()
    mb.push((5.30, 5.35, 1.30), math.pi)
    furn.poster(mb, 0.62, 0.88, "screen_ui")
    mb.pop()
    mb.build()

    # --------------------------------------------------------------- signs
    objs = []
    objs.append(sign("24H", (5.62, 5.38, 2.22), math.pi, 0.30, "neon_magenta", 0.03))
    objs.append(sign("NOODLE//BAR", (4.18, 3.55, 2.55), math.pi, 0.20, "neon_cyan", 0.02))
    objs.append(sign("01", (11.28, 4.45, 1.05), -math.pi / 2, 0.34, "neon_cyan", 0.03))
    for o in objs:
        if o:
            o.data.materials.clear()
            o.data.materials.append(cy.mat("neon_magenta" if "24H" in o.name else "neon_cyan"))

    objs_n = len(bpy.data.collections[COL].objects)
    tris = 0
    for o in bpy.data.collections[COL].objects:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
    return {"objects": objs_n, "tris": tris,
            "names": sorted(o.name for o in bpy.data.collections[COL].objects)}


_result = build()
print(_result, flush=True)
