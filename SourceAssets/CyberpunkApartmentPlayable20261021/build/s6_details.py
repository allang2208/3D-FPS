"""s6 - cyberpunk detail layer: conduits, pipes, sensors, greeble, balcony set."""
from __future__ import annotations

import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402
import furn  # noqa: E402


def pipe_run(mb, pts, r=0.035, key="metal_steel", clamps=True, every=1.2):
    """Pipe polyline with flanges at joints and wall clamps."""
    mb.tube(pts, r, key, seg=10)
    for i in range(len(pts) - 1):
        a, b = cy.Vector(pts[i]), cy.Vector(pts[i + 1])
        d = (b - a)
        ln = d.length
        if ln < 1e-4:
            continue
        n = max(1, int(ln / every))
        for k in range(n + 1):
            p = a + d * (k / n)
            if k in (0, n):
                # flange
                mb.cyl(r * 1.45, 0.03, tuple(p), rot=(0, 0, 0), seg=12, key="metal_black")
            elif clamps and k % 2 == 1:
                mb.box((0.05, 0.05, 0.05), tuple(p), (0, 0, 0), "metal_black")


def conduit(mb, x0, x1, y, z, n=3, drop=None):
    for i in range(n):
        zz = z - i * 0.055
        mb.tube([(x0, y + i * 0.02, zz), (x1, y + i * 0.02, zz)], 0.012,
                ["metal_steel", "metal_black", "plastic_black"][i % 3], seg=6)
    # clamps
    k = x0
    while k < x1:
        mb.box((0.03, 0.09, 0.13), (k, y + 0.02, z - 0.055), key="metal_black")
        k += 0.9


def build() -> dict:
    cy.reset_col("DETAILS")
    cy.reset_col("BALCONY")
    rng = random.Random(31337)

    # =====================================================================
    # ceiling services
    # =====================================================================
    mb = cy.MB("DET_ceiling_services", "DETAILS", bevel=0.002)
    Z = 2.86
    # main pipe run down the corridor, turning into the kitchen
    pipe_run(mb, [(0.30, 5.95, Z), (11.10, 5.95, Z)], 0.045, "metal_steel")
    pipe_run(mb, [(0.30, 6.28, Z - 0.10), (8.70, 6.28, Z - 0.10), (8.70, 10.60, Z - 0.10)],
             0.028, "metal_rust")
    pipe_run(mb, [(4.20, 6.10, Z - 0.16), (4.20, 10.70, Z - 0.16)], 0.022, "metal_copper")
    # living room sprinkler main
    pipe_run(mb, [(4.10, 0.40, Z - 0.04), (11.20, 0.40, Z - 0.04)], 0.032, "metal_steel")
    # cable tray along the living ceiling
    mb.box((7.0, 0.22, 0.05), (7.60, 5.10, Z - 0.02), key="metal_steel")
    for i in range(10):
        mb.box((0.02, 0.20, 0.06), (4.2 + i * 0.72, 5.10, Z - 0.01), key="metal_black")
    for i in range(6):
        mb.tube([(4.2, 5.00 + i * 0.028, Z - 0.05), (10.9, 5.00 + i * 0.028, Z - 0.05)],
                0.008, ["plastic_black", "neon_cyan" if i == 3 else "plastic_black",
                        "metal_copper"][i % 3], seg=5)
    conduit(mb, 4.15, 11.15, 0.30, Z - 0.02, n=3)
    conduit(mb, 0.25, 4.60, 5.66, Z - 0.02, n=2)
    # vertical drops through the slab
    for (x, y) in [(4.30, 5.95), (10.95, 5.95), (8.60, 6.30)]:
        mb.cyl(0.05, 0.30, (x, y, 2.70), seg=12, key="metal_black")
        mb.cyl(0.065, 0.02, (x, y, 2.56), seg=12, key="metal_steel")
    # vents
    for (x, y) in [(5.20, 4.10), (9.60, 4.10), (6.60, 2.10)]:
        mb.box((0.60, 0.22, 0.035), (x, y, 2.925), key="metal_steel")
        for i in range(6):
            mb.box((0.56, 0.012, 0.006), (x, y - 0.08 + i * 0.032, 2.905), key="metal_black")
    # smoke detectors / sprinkler heads / speakers
    for (x, y) in [(5.0, 2.0), (9.0, 2.0), (6.5, 4.6), (2.0, 3.0), (13.0, 3.0),
                   (13.0, 8.0), (6.0, 8.5), (1.5, 9.5), (9.9, 9.0)]:
        mb.cyl(0.075, 0.03, (x, y, 2.925), seg=18, key="plastic_white")
        mb.cyl(0.02, 0.006, (x, y, 2.905), seg=10, key="neon_green")
        mb.cyl(0.012, 0.09, (x + 0.16, y, 2.88), seg=8, key="metal_steel")
        mb.cyl(0.03, 0.015, (x + 0.16, y, 2.845), seg=10, key="metal_steel")
    # ceiling speakers
    for (x, y) in [(5.30, 1.10), (9.80, 1.10), (5.30, 4.60), (9.80, 4.60)]:
        mb.cyl(0.11, 0.06, (x, y, 2.90), seg=20, key="plastic_black")
        mb.cyl(0.085, 0.008, (x, y, 2.868), seg=18, key="metal_dark")
    mb.build()

    # =====================================================================
    # wall services / greeble
    # =====================================================================
    mb = cy.MB("DET_wall_greeble", "DETAILS", bevel=0.002)
    # breaker panel in the corridor
    mb.push((8.15, 6.68, 1.35))
    mb.box((0.42, 0.10, 0.50), (0, 0, 0), key="metal_steel")
    mb.box((0.38, 0.02, 0.46), (0, -0.06, 0), key="tech_panel")
    for i in range(3):
        mb.box((0.03, 0.01, 0.03), (-0.12 + i * 0.11, -0.075, 0.16), key="neon_green")
    mb.pop()
    # wall conduit drops
    for (x, y) in [(4.06, 4.90), (11.22, 1.60), (8.84, 8.00), (2.90, 9.90), (15.80, 7.10)]:
        mb.tube([(x, y, 2.80), (x, y, 0.30)], 0.018, "metal_steel", seg=6)
        for k in range(5):
            mb.box((0.06, 0.06, 0.03), (x, y, 0.6 + k * 0.5), key="metal_black")
    # junction boxes
    for (x, y, z) in [(4.06, 4.90, 0.35), (11.22, 1.60, 2.45), (8.84, 8.00, 1.10),
                      (2.90, 9.90, 2.20), (15.80, 7.10, 0.95)]:
        mb.box((0.14, 0.09, 0.14), (x, y, z), key="metal_steel")
        mb.box((0.10, 0.01, 0.10), (x, y - 0.048, z), key="tech_panel")
    # door keypad next to each interior door
    for (x, y, rz) in [(2.55, 5.44, 0), (11.30, 4.60, math.pi / 2), (2.10, 8.18, 0),
                       (4.20, 8.18, 0), (11.28, 8.05, math.pi / 2)]:
        mb.box((0.09, 0.04, 0.14), (x, y, 1.45), (0, 0, rz), "tech_panel")
        mb.box((0.05, 0.006, 0.03), (x, y - 0.022, 1.48), (0, 0, rz), "screen_ui")
    # AC indoor unit in the living room
    mb.push((10.90, 4.85, 2.52), -math.pi / 2)
    furn.ac_indoor(mb, 0.92, 0.30, 0.22)
    mb.pop()
    mb.push((13.20, 5.32, 2.52), math.pi)
    furn.ac_indoor(mb, 0.86, 0.28, 0.21)
    mb.pop()
    # camera domes
    for (x, y, z) in [(4.10, 5.40, 2.72), (11.30, 6.60, 2.72), (8.80, 10.80, 2.72)]:
        mb.cyl(0.055, 0.03, (x, y, z), seg=16, key="plastic_white")
        mb.sphere(0.045, (x, y, z - 0.03), seg=14, rings=8, key="glass_black", squash=0.8)
    # wall panels (tech) at strategic spots
    for (cx, cyy, cz, w, h, rz) in [
        (4.00, 4.55, 1.55, 0.60, 0.80, math.pi / 2),
        (11.30, 3.55, 1.75, 0.55, 1.40, -math.pi / 2),
        (8.84, 7.30, 1.60, 0.50, 0.90, math.pi / 2),
        (8.40, 6.74, 1.90, 0.70, 0.50, 0),
    ]:
        mb.push((cx, cyy, cz), rz)
        mb.box((w, 0.03, h), (0, 0, 0), key="tech_panel")
        mb.box((w - 0.04, 0.006, h - 0.04), (0, -0.02, 0), key="circuit")
        mb.box((w - 0.06, 0.01, 0.012), (0, -0.024, h / 2 - 0.05), key="neon_strip_cool")
        mb.pop()
    # emergency exit sign over the entry
    mb.box((0.44, 0.06, 0.16), (9.92, 10.84, 2.42), key="metal_black")
    mb.box((0.40, 0.01, 0.12), (9.92, 10.80, 2.42), key="neon_green")
    mb.build()

    # =====================================================================
    # floor details
    # =====================================================================
    mb = cy.MB("DET_floor", "DETAILS", bevel=0.001)
    # floor cable duct in the living room
    mb.push((8.25, 4.60, 0))
    mb.box((1.80, 0.10, 0.02), (0, 0, 0.01), key="metal_steel")
    mb.pop()
    # rugs edge shadow strips / iron thresholds
    for (x, y, w, d) in [(3.90, 5.40, 0.14, 0.12), (11.34, 5.40, 0.14, 0.12),
                         (1.97, 5.46, 0.94, 0.10), (4.50, 5.46, 3.0, 0.10),
                         (6.70, 6.78, 2.6, 0.10)]:
        mb.box((w, d, 0.014), (x, y, 0.007), key="metal_steel")
    # wet patches by the balcony door
    for (x, y, sx, sy) in [(8.30, 0.35, 0.95, 0.55), (9.10, 0.20, 0.55, 0.35)]:
        mb.push((x, y, 0.004))
        mb.disc(1.0, (0, 0, 0), rot=(0, 0, 0), seg=28, key="puddle")
        mb.pop()
    mb.build()

    # =====================================================================
    # wires, straps, small clutter
    # =====================================================================
    mb = cy.MB("DET_wires", "DETAILS", bevel=0.0)
    for i in range(4):
        mb.tube(cy.catenary((4.20, 2.90 + i * 0.12, 2.60), (4.20, 4.90, 1.40), 0.22, 12),
                0.006, "plastic_black")
    mb.tube(cy.catenary((10.90, 1.20, 2.30), (10.90, 3.90, 2.10), 0.30, 14), 0.008,
            "plastic_black")
    mb.tube(cy.catenary((11.10, 6.40, 2.60), (11.10, 9.90, 1.90), 0.35, 14), 0.007,
            "plastic_black")
    mb.build()

    # =====================================================================
    # graffiti + stickers on balcony fins
    # =====================================================================
    mb = cy.MB("DET_graffiti", "DETAILS", bevel=0.0)
    mb.push((4.08, -1.70, 1.10), math.pi / 2)
    mb.plane(1.30, 0.95, (0, 0, 0), rot=(0, 0, 0), key="wall_graffiti")
    mb.pop()
    mb.push((11.22, -2.10, 0.85), -math.pi / 2)
    mb.plane(1.10, 0.80, (0, 0, 0), rot=(0, 0, 0), key="wall_graffiti")
    mb.pop()
    # stickers on the fridge / tv console
    for i in range(5):
        mb.push((8.60 + (i % 2) * 0.10, 10.16, 1.05 + (i // 2) * 0.12), 0)
        mb.box((0.07, 0.004, 0.07), (0, 0, 0), (0, 0, i * 0.4),
               ["neon_magenta", "neon_cyan", "neon_amber", "holo_panel", "neon_green"][i])
        mb.pop()
    mb.build()

    # =====================================================================
    # balcony
    # =====================================================================
    mb = cy.MB("BAL_furniture", "BALCONY", bevel=0.003)
    # outdoor sofa against the railing
    mb.push((5.45, -2.32, -0.03), 0.0)
    furn.sofa(mb, w=2.10, d=0.86, seats=2, key="fabric_navy", arm_key="fabric_navy")
    mb.pop()
    # low table
    mb.push((7.55, -2.20, -0.03))
    mb.box((1.05, 0.60, 0.05), (0, 0, 0.36), key="wood_oak")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((0.04, 0.04, 0.34), (sx * 0.46, sy * 0.24, 0.17), key="metal_black")
    mb.box((0.90, 0.46, 0.02), (0, 0, 0.10), key="metal_black")
    mb.pop()
    # planters along the railing
    for x in (4.70, 10.55):
        mb.push((x, -2.55, -0.03))
        mb.box((0.90, 0.34, 0.46), (0, 0, 0.23), key="concrete_raw")
        mb.box((0.84, 0.28, 0.04), (0, 0, 0.44), key="soil")
        furn.plant_bamboo(mb, random.Random(int(x * 10)), n=6, scale=0.72)
        mb.pop()
    # AC condensers on brackets against the fin
    for (x, y, z) in [(4.40, -0.62, 0.55), (4.40, -1.42, 0.55)]:
        mb.push((x, y, z))
        furn.ac_outdoor(mb, 0.86, 0.72, 0.34)
        mb.pop()
        mb.box((0.90, 0.06, 0.05), (x, y, z - 0.02), key="metal_steel")
    # drying rack
    mb.push((10.55, -1.30, 0))
    for sx in (-1, 1):
        mb.cyl(0.016, 1.05, (sx * 0.42, 0, 0.52), seg=8, key="metal_steel")
    for i in range(5):
        mb.cyl(0.008, 0.86, (0, 0, 0.30 + i * 0.18), rot=(0, math.pi / 2, 0), seg=6,
               key="metal_steel")
    mb.box((0.30, 0.02, 0.42), (-0.20, 0.01, 0.72), key="fabric_cream")
    mb.box((0.22, 0.02, 0.36), (0.18, 0.01, 0.66), key="fabric_navy")
    mb.pop()
    # telescope
    mb.push((9.85, -2.42, -0.03))
    for i in range(3):
        a = i * 2.094
        mb.cyl(0.014, 0.95, (0.16 * math.cos(a), 0.16 * math.sin(a), 0.47),
               (0.12 * math.sin(a), -0.12 * math.cos(a), 0), seg=8, key="metal_black")
    mb.cyl(0.05, 0.16, (0, 0, 0.95), seg=12, key="metal_black")
    mb.cyl(0.055, 0.55, (0.02, -0.10, 1.10), (1.15, 0, 0.15), seg=14, key="metal_steel",
           r2=0.075)
    mb.cyl(0.06, 0.04, (0.02, -0.34, 1.24), (1.15, 0, 0.15), seg=14, key="glass_black")
    mb.pop()
    # bar cart
    mb.push((8.55, -0.55, -0.03))
    mb.box((0.70, 0.40, 0.03), (0, 0, 0.62), key="metal_gold")
    mb.box((0.70, 0.40, 0.03), (0, 0, 0.20), key="metal_gold")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.012, 0.62, (sx * 0.33, sy * 0.18, 0.31), seg=6, key="metal_gold")
    mb.pop()
    # lanterns hanging under the soffit
    for x in (5.0, 6.6, 8.2, 9.8):
        mb.push((x, -1.20, 2.90))
        mb.cyl(0.006, 0.32, (0, 0, -0.16), seg=6, key="metal_black")
        mb.cyl(0.075, 0.20, (0, 0, -0.42), seg=14, key="metal_black", r2=0.06)
        mb.sphere(0.035, (0, 0, -0.44), seg=8, rings=6, key="lamp_bulb")
        mb.pop()
    mb.build()

    mb = cy.MB("BAL_detail", "BALCONY", bevel=0.001)
    # string lights along the railing
    for i in range(9):
        x0 = 4.10 + i * 0.82
        x1 = x0 + 0.82
        mb.tube(cy.catenary((x0, -2.76, 1.04), (x1, -2.76, 1.04), 0.10, 8), 0.004,
                "plastic_black")
        mb.sphere(0.016, ((x0 + x1) / 2, -2.76, 0.96), seg=6, rings=4, key="lamp_bulb")
    # ashtray + bottles + can on the table
    mb.push((7.35, -2.30, 0.36))
    mb.cyl(0.075, 0.035, (0, 0, 0.017), seg=16, key="glass_black")
    mb.pop()
    mb.push((7.80, -2.25, 0.36))
    furn.bottle(mb, 0.24, 0.034, "glass_black", "metal_gold")
    mb.pop()
    mb.push((7.95, -2.05, 0.36))
    furn.can(mb, 0.033, 0.12, "neon_cyan")
    mb.pop()
    # puddle on the deck
    mb.push((6.60, -1.10, -0.026))
    mb.disc(1.0, (0, 0, 0), rot=(0, 0, 0), seg=32, key="puddle")
    mb.pop()
    mb.push((9.60, -0.60, -0.026))
    mb.disc(0.7, (0, 0, 0), rot=(0, 0, 0), seg=26, key="puddle")
    mb.pop()
    # bucket + mop + crate
    mb.push((4.55, -0.35, -0.03))
    mb.cyl(0.14, 0.30, (0, 0, 0.15), seg=16, key="plastic_white", r2=0.16)
    mb.pop()
    mb.push((10.95, -0.45, -0.03))
    mb.box((0.42, 0.32, 0.28), (0, 0, 0.14), key="wood_oak")
    for i in range(4):
        mb.box((0.40, 0.02, 0.02), (0, -0.16, 0.05 + i * 0.07), key="wood_walnut")
    mb.pop()
    mb.build()

    # balcony neon sign on the soffit
    ob = cy.text_mesh("BAL_sign", "NIGHT CITY", 0.26, (7.60, -0.30, 0.55),
                      rot=(math.pi / 2, 0, 0), key="neon_magenta", extrude=0.02,
                      col_name="BALCONY")
    # holo emitter on the table
    mb = cy.MB("BAL_holo", "BALCONY", bevel=0.0)
    mb.push((7.55, -2.20, 0.41))
    furn.holo_emitter(mb, 0.11, 0.05)
    mb.pop()
    mb.push((7.55, -2.20, 0.62))
    mb.plane(0.42, 0.42, (0, 0, 0), rot=(math.pi / 2, 0, 0.4), key="holo_cyan")
    mb.pop()
    mb.build()

    # =====================================================================
    # facade greeble (outside, under the balcony slab)
    # =====================================================================
    mb = cy.MB("DET_facade_out", "DETAILS", bevel=0.002)
    # drip line + brackets under the balcony soffit
    mb.box((7.4, 0.06, 0.06), (7.60, -2.86, 2.99), key="metal_steel")
    for i in range(6):
        mb.box((0.05, 0.10, 0.16), (4.2 + i * 1.4, -2.86, 3.08), key="metal_black")
    # exterior drain pipes
    for x in (4.06, 11.22):
        mb.cyl(0.055, 2.9, (x, -2.92, 1.45), seg=12, key="metal_rust")
        for k in range(4):
            mb.cyl(0.07, 0.04, (x, -2.92, 0.3 + k * 0.8), seg=12, key="metal_black")
    mb.build()

    cols = ["DETAILS", "BALCONY"]
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
    return {"objects": objs, "tris": tris,
            "cols": [[c, len(bpy.data.collections[c].objects)] for c in cols]}


_result = build()
print(_result, flush=True)