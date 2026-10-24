"""s3 - kitchen + dining (X 4.80..8.64, Y 6.84..10.88)."""
from __future__ import annotations

import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402
import furn  # noqa: E402

COL = "KITCHEN"


def build() -> dict:
    cy.reset_col(COL)
    rng = random.Random(77)

    # ------------------------------------------------------ counters/cabinets
    mb = cy.MB("KIT_run", COL, bevel=0.003)
    mb.push((4.90, 10.56, 0))
    furn.kitchen_run(mb, length=3.10, depth=0.63, height=0.90, sink_at=2.55, hob_at=0.95)
    mb.pop()
    mb.push((5.00, 10.72, 0))
    furn.upper_cabinets(mb, length=2.85, z0=1.52, z1=2.38, depth=0.34)
    mb.pop()
    # fridge (end of the run)
    mb.push((8.32, 10.52, 0))
    furn.fridge(mb, 0.75, 0.68, 2.02)
    mb.pop()
    # range hood over the hob
    mb.push((5.85, 10.42, 2.12))
    furn.range_hood(mb, 0.92, 0.52, 0.20)
    mb.pop()
    # tall pantry on the west wall
    mb.push((4.96, 7.35, 0), math.pi / 2)
    mb.box((1.10, 0.42, 2.10), (0, 0, 1.05), key="wood_dark")
    for i in range(3):
        mb.box((1.02, 0.02, 0.60), (0, -0.22, 0.45 + i * 0.66), key="wood_walnut")
        mb.box((0.20, 0.014, 0.014), (0, -0.235, 0.45 + i * 0.66), key="metal_gold")
    mb.pop()
    # open shelf with pots, above the counter
    mb.push((4.90, 10.62, 1.52))
    mb.box((1.05, 0.28, 0.03), (0.5, 0, 0.0), key="wood_dark")
    for i in range(3):
        mb.cyl(0.09 + i * 0.015, 0.11, (0.18 + i * 0.30, 0, 0.075), seg=18, key="metal_steel")
    mb.box((1.05, 0.02, 0.03), (0.5, -0.14, 0.0), key="metal_gold")
    mb.pop()
    mb.build()

    # --------------------------------------------------------------- dining
    mb = cy.MB("KIT_dining", COL, bevel=0.003)
    mb.push((6.70, 8.15, 0))
    furn.dining_table(mb, w=1.70, d=0.95, h=0.75)
    mb.pop()
    for (x, y, rz) in [(6.10, 7.80, 0.05), (7.30, 7.80, -0.06),
                       (6.10, 8.95, math.pi - 0.05), (7.30, 8.95, math.pi + 0.06)]:
        mb.push((x, y, 0), rz)
        furn.dining_chair(mb)
        mb.pop()
    mb.build()

    # ------------------------------------------------------------ pendants
    mb = cy.MB("KIT_pendants", COL, bevel=0.001)
    for x in (5.95, 6.70, 7.45):
        mb.push((x, 8.15, 2.95))
        furn.pendant(mb, drop=1.28, r=0.13)
        mb.pop()
    mb.build()

    # ------------------------------------------------------------- clutter
    mb = cy.MB("KIT_clutter", COL, bevel=0.001)
    # counter top: board, knives, kettle, jars, bowls, dish rack
    mb.push((5.15, 10.30, 0.92))
    mb.box((0.42, 0.30, 0.02), (0, 0, 0.01), (0, 0, 0.15), "wood_oak")
    mb.box((0.20, 0.06, 0.10), (0.28, 0, 0.05), (0, 0, 0.15), "metal_black")
    for i in range(4):
        mb.box((0.012, 0.025, 0.16), (0.24 + i * 0.025, 0, 0.14), (0.2, 0, 0.15), "metal_steel")
    mb.pop()
    mb.push((6.55, 10.35, 0.92))
    mb.cyl(0.075, 0.20, (0, 0, 0.10), seg=18, key="metal_steel")
    mb.cyl(0.05, 0.03, (0, 0, 0.215), seg=14, key="plastic_black")
    mb.tube([(-0.07, 0, 0.12), (-0.14, 0, 0.06), (-0.09, 0, 0.02)], 0.012, "plastic_black", seg=6)
    mb.pop()
    for i, x in enumerate((7.35, 7.60, 7.85)):
        mb.push((x, 10.68, 0.92))
        mb.cyl(0.045, 0.14 + i * 0.04, (0, 0, 0.07 + i * 0.02), seg=14, key="glass_window")
        mb.cyl(0.05, 0.02, (0, 0, 0.15 + 0.07 + i * 0.04 - 0.03), seg=14, key="metal_gold")
        mb.pop()
    mb.push((6.05, 10.30, 0.92))
    furn.bowl(mb, 0.13, 0.08, "ceramic_white")
    mb.pop()
    mb.push((6.05, 10.30, 0.92))
    for i in range(4):
        mb.sphere(0.038, (-0.04 + i * 0.05, -0.02 + (i % 2) * 0.04, 0.09 + (i % 3) * 0.02),
                  seg=10, rings=7, key="neon_amber")
    mb.pop()
    # dirty dishes by the sink
    mb.push((7.60, 10.32, 0.92))
    for i in range(3):
        mb.cyl(0.11, 0.012, (0.02 * i, 0.02 * i, 0.10 + i * 0.018), seg=20, key="ceramic_white")
    mb.pop()
    # pantry items
    for i in range(5):
        mb.push((5.00, 6.95 + i * 0.22, 0.55))
        mb.cyl(0.045, 0.20, (0, 0, 0.10), seg=12, key="glass_black")
        mb.pop()
    # hanging utensils
    for i in range(5):
        mb.push((5.35 + i * 0.16, 10.05, 2.02))
        mb.cyl(0.006, 0.28, (0, 0, -0.14), seg=6, key="metal_steel")
        mb.box((0.03, 0.02, 0.10), (0, 0, -0.31), key="metal_steel")
        mb.pop()
    # trash bin
    mb.push((8.30, 7.05, 0))
    mb.cyl(0.17, 0.60, (0, 0, 0.30), seg=20, key="metal_steel")
    mb.cyl(0.175, 0.03, (0, 0, 0.61), seg=20, key="metal_black")
    mb.pop()
    mb.build()

    # --------------------------------------------------------------- LEDs
    mb = cy.MB("KIT_light", COL, bevel=0.0)
    furn.led_strip(mb, (4.95, 10.30, 0.905), (8.00, 10.30, 0.905), "neon_strip_warm", 0.02)
    furn.led_strip(mb, (5.00, 10.16, 1.50), (7.85, 10.16, 1.50), "neon_strip_warm", 0.016)
    mb.build()

    tris = 0
    for o in bpy.data.collections[COL].objects:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
    return {"objects": len(bpy.data.collections[COL].objects), "tris": tris}


_result = build()
print(_result, flush=True)