"""furn — parametric furniture & prop library.

Local convention: origin at floor centre, front facing -Y, Z up.
Every builder writes into an MB (so many pieces end up in one object).

    mb = cy.MB("LIVING_furniture", "LIVING", bevel=0.004)
    furn.sofa(mb, w=3.2)
    mb.push((8.0, 2.6, 0)); furn.coffee_table(mb); mb.pop()
"""
from __future__ import annotations

import math
import random

import cy_lib as cy


def _r(rng, a, b):
    return a + (b - a) * rng.random()


# ---------------------------------------------------------------------------
# seating
# ---------------------------------------------------------------------------


def sofa(mb, w=3.2, d=1.02, seat_h=0.44, back_h=0.82, seats=3,
         key="fabric", arm_key="fabric", leg_key="metal_dark", chaise=0.0):
    """Low modular sofa: rounded plinth, domed cushions, leaning back pads."""
    depth = d
    # plinth: soft-edged body sitting on a recessed base
    superbox(mb, (w, depth, 0.34), (0, 0, 0.26), e=0.28, seg=34, rings=14, key=arm_key)
    superbox(mb, (w - 0.06, depth - 0.08, 0.10), (0, 0, 0.085), e=0.20, seg=28, rings=10,
             key=leg_key)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.022, 0.075, (sx * (w / 2 - 0.10), sy * (depth / 2 - 0.10), 0.038),
                   seg=12, key=leg_key)
    # seat cushions: domed superellipsoids with a front overhang
    cw = (w - 0.18) / seats
    for i in range(seats):
        x = -w / 2 + 0.09 + cw * (i + 0.5)
        superbox(mb, (cw - 0.014, depth - 0.22, 0.20), (x, -0.02, 0.47),
                 e=0.30, seg=34, rings=16, key=key, wrinkle=0.0055, seed=i * 2.7 + 1.0)
        superbox(mb, (cw - 0.05, depth - 0.26, 0.10), (x, -0.02, 0.545),
                 e=0.42, seg=30, rings=12, key=key, wrinkle=0.0045, seed=i * 3.9)
        # seam shadow between cushions
        mb.box((0.006, depth - 0.26, 0.13), (x + cw / 2 - 0.004, -0.02, 0.44),
               key="fabric_grey")
        # back pad, tilted back
        superbox(mb, (cw - 0.035, 0.20, 0.50), (x, depth / 2 - 0.20, 0.72),
                 e=0.40, seg=30, rings=16, key=key, rot=(-0.16, 0, 0),
                 wrinkle=0.0065, seed=i * 5.3 + 0.4)
    # back rest core
    superbox(mb, (w, 0.20, 0.58), (0, depth / 2 - 0.09, 0.60),
             e=0.30, seg=32, rings=14, key=arm_key)
    # arms: rounded rolls with a flat top pad
    for sx in (-1, 1):
        superbox(mb, (0.19, depth - 0.02, 0.34), (sx * (w / 2 - 0.075), 0, 0.53),
                 e=0.34, seg=26, rings=14, key=arm_key)
        superbox(mb, (0.185, 0.34, 0.055), (sx * (w / 2 - 0.075), -depth / 2 + 0.22, 0.585),
                 e=0.45, seg=22, rings=8, key=arm_key)
    if chaise > 0:
        superbox(mb, (chaise, depth - 0.10, 0.34), (w / 2 + chaise / 2 - 0.02, 0, 0.28),
                 e=0.30, seg=26, rings=12, key=arm_key)
        superbox(mb, (chaise - 0.04, depth - 0.24, 0.19),
                 (w / 2 + chaise / 2 - 0.02, -0.02, 0.47),
                 e=0.34, seg=26, rings=12, key=key)


def armchair(mb, w=0.92, d=0.92, key="fabric", leg_key="metal_dark", tilt=0.0):
    """Lounge chair: rounded shell, domed seat, tapered metal legs."""
    superbox(mb, (w, d, 0.30), (0, 0, 0.34), e=0.28, seg=30, rings=13, key=key)
    superbox(mb, (w - 0.07, d - 0.07, 0.16), (0, -0.02, 0.50),
             e=0.34, seg=28, rings=12, key=key)
    superbox(mb, (w - 0.02, 0.17, 0.52), (0, d / 2 - 0.08, 0.60),
             e=0.40, seg=26, rings=13, key=key, rot=(tilt - 0.14, 0, 0))
    for sx in (-1, 1):
        superbox(mb, (0.12, d - 0.03, 0.30), (sx * (w / 2 - 0.06), 0, 0.50),
                 e=0.36, seg=22, rings=12, key=key)
        for sy in (-1, 1):
            mb.cyl(0.014, 0.22, (sx * (w / 2 - 0.085), sy * (d / 2 - 0.085), 0.11),
                   seg=12, key=leg_key, r2=0.010)
    superbox(mb, (w - 0.05, d - 0.05, 0.045), (0, 0, 0.20), e=0.22, seg=24, rings=8,
             key="metal_dark")


def dining_chair(mb, key_seat="fabric_grey", key_frame="wood_walnut"):
    """Dining chair: padded seat, steam-bent backrest, splayed tapered legs."""
    superbox(mb, (0.44, 0.44, 0.06), (0, 0, 0.45), e=0.24, seg=26, rings=10,
             key=key_frame)
    superbox(mb, (0.40, 0.38, 0.055), (0, 0.008, 0.482), e=0.40, seg=26, rings=10,
             key=key_seat)
    # bent backrest: three stacked slats following an arc
    for k, (zz, ww, hh) in enumerate(((0.60, 0.36, 0.075), (0.69, 0.35, 0.070),
                                      (0.77, 0.33, 0.065))):
        segs = 7
        pts = []
        for i in range(segs + 1):
            t = i / segs
            xx = (t - 0.5) * ww
            yy = 0.195 - 0.055 * (1.0 - math.cos((t - 0.5) * 2.4))
            pts.append((xx, yy, zz + 0.012 * math.sin(math.pi * t)))
        tube_prof = []
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            for dz in (-hh / 2, hh / 2):
                tube_prof.append((a[0], a[1], a[2] + dz))
            tube_prof.append((b[0], b[1], b[2] - hh / 2))
            tube_prof.append((b[0], b[1], b[2] + hh / 2))
        # simple slab through the arc (cheap and reads as a bent slat)
        verts = []
        for i, p in enumerate(pts):
            verts.append((p[0], p[1] - 0.014, p[2] - hh / 2))
            verts.append((p[0], p[1] + 0.014, p[2] - hh / 2))
            verts.append((p[0], p[1] + 0.014, p[2] + hh / 2))
            verts.append((p[0], p[1] - 0.014, p[2] + hh / 2))
        faces = []
        for i in range(segs):
            a = i * 4
            b = (i + 1) * 4
            for k2 in range(4):
                k3 = (k2 + 1) % 4
                faces.append((a + k2, a + k3, b + k3, b + k2))
        faces.append((0, 3, 2, 1))
        a = segs * 4
        faces.append((a, a + 1, a + 2, a + 3))
        mb.add(verts, faces, key_frame)
    # vertical stiles tying the backrest to the seat
    for sx in (-1, 1):
        mb.cyl(0.011, 0.32, (sx * 0.165, 0.195, 0.60), seg=10, key=key_frame)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.017, 0.45, (sx * 0.175, sy * 0.175, 0.225),
                   rot=(sy * 0.045, -sx * 0.045, 0), seg=10, key=key_frame, r2=0.011)
    mb.box((0.34, 0.016, 0.016), (0, -0.185, 0.14), key=key_frame)
    mb.box((0.34, 0.016, 0.016), (0, 0.185, 0.14), key=key_frame)


def stool(mb, h=0.72, r=0.17, key_seat="leather", key_leg="metal_chrome"):
    mb.cyl(r, 0.05, (0, 0, h), seg=20, key=key_seat)
    for i in range(3):
        a = i * 2.094
        x, y = 0.13 * math.cos(a), 0.13 * math.sin(a)
        mb.cyl(0.016, h, (x, y, h / 2), rot=(0.09 * math.cos(a + 1.5), 0.09 * math.sin(a + 1.5), 0),
               seg=8, key=key_leg)
    mb.cyl(0.12, 0.014, (0, 0, 0.22), seg=16, key=key_leg)


# ---------------------------------------------------------------------------
# tables & storage
# ---------------------------------------------------------------------------


def coffee_table(mb, w=1.7, d=0.95, h=0.36, key_top="marble", key_frame="metal_black"):
    """Low table: rounded stone slab on a hairpin-ish steel frame with a shelf."""
    superbox(mb, (w, d, 0.055), (0, 0, h), e=0.16, seg=34, rings=10, key=key_top)
    superbox(mb, (w - 0.10, d - 0.10, 0.025), (0, 0, h - 0.040),
             e=0.18, seg=30, rings=8, key=key_frame)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.019, h - 0.06, (sx * (w / 2 - 0.075), sy * (d / 2 - 0.075), (h - 0.06) / 2),
                   seg=12, key=key_frame, r2=0.014)
    superbox(mb, (w - 0.22, d - 0.22, 0.028), (0, 0, 0.105),
             e=0.20, seg=28, rings=8, key=key_frame)
    # cross braces under the shelf
    for sx in (-1, 1):
        mb.cyl(0.008, d - 0.24, (sx * (w / 2 - 0.075), 0, 0.075), rot=(math.pi / 2, 0, 0),
               seg=8, key=key_frame)
    # books + tray on top
    mb.box((0.30, 0.22, 0.035), (-0.35, 0.05, h + 0.043), (0, 0, 0.12), "paper")
    mb.box((0.28, 0.20, 0.03), (-0.36, 0.06, h + 0.075), (0, 0, 0.05), "paper_dark")
    mb.cyl(0.09, 0.012, (0.30, -0.05, h + 0.032), seg=20, key="metal_gold")
    mb.cyl(0.035, 0.10, (0.45, 0.12, h + 0.077), seg=16, key="ceramic_white")


def side_table(mb, r=0.22, h=0.55):
    mb.cyl(r, 0.04, (0, 0, h), seg=24, key="marble")
    mb.cyl(0.022, h, (0, 0, h / 2), seg=10, key="metal_dark")
    mb.cyl(r * 0.7, 0.02, (0, 0, 0.012), seg=20, key="metal_dark")


def dining_table(mb, w=1.6, d=0.9, h=0.75, key_top="wood_dark", key_leg="metal_black"):
    mb.box((w, d, 0.045), (0, 0, h), key=key_top)
    mb.box((w - 0.10, d - 0.10, 0.05), (0, 0, h - 0.05), key=key_leg)
    for sx in (-1, 1):
        mb.box((0.06, d - 0.16, h - 0.08), (sx * (w / 2 - 0.10), 0, (h - 0.08) / 2), key=key_leg)
        mb.box((0.10, d - 0.10, 0.02), (sx * (w / 2 - 0.10), 0, 0.01), key=key_leg)
    # table setting: plates, glasses, bottle
    for i in (-1, 1):
        mb.cyl(0.115, 0.012, (i * 0.36, 0.0, h + 0.028), seg=24, key="ceramic_white")
        mb.cyl(0.038, 0.09, (i * 0.36, -0.24, h + 0.07), seg=12, key="glass_window")
        mb.cyl(0.006, 0.16, (i * 0.36, -0.31, h + 0.10), seg=8, key="metal_steel")
    mb.cyl(0.045, 0.26, (0, 0.02, h + 0.16), seg=14, key="glass_black")
    mb.cyl(0.014, 0.08, (0, 0.02, h + 0.31), seg=8, key="glass_black")


def console_table(mb, w=1.8, d=0.36, h=0.80):
    mb.box((w, d, 0.04), (0, 0, h), key="marble")
    mb.box((w - 0.06, d - 0.03, 0.02), (0, 0, h - 0.03), key="metal_black")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((0.03, 0.03, h), (sx * (w / 2 - 0.05), sy * (d / 2 - 0.04), h / 2), key="metal_black")
    for sx in (-1, 1):
        mb.box((0.03, d - 0.04, 0.02), (sx * (w / 2 - 0.05), 0, 0.14), key="metal_black")
    mb.box((w - 0.1, d - 0.06, 0.02), (0, 0, 0.15), key="metal_black")
    # key bowl + parcel
    mb.cyl(0.10, 0.045, (-0.5, 0, h + 0.043), seg=20, key="metal_gold")
    mb.box((0.34, 0.24, 0.20), (0.45, 0, h + 0.12), (0, 0, 0.18), "paper")


def shelves(mb, w=2.0, h=2.0, d=0.32, n=4, key="wood_walnut", key_metal="metal_black",
            books=True, rng=None):
    rng = rng or random.Random(7)
    for sx in (-1, 1):
        mb.box((0.04, d, h), (sx * (w / 2 - 0.02), 0, h / 2), key=key_metal)
    for i in range(n + 1):
        z = 0.06 + i * (h - 0.10) / n
        mb.box((w, d, 0.03), (0, 0, z), key=key)
    mb.box((w, 0.02, h), (0, d / 2 - 0.01, h / 2), key="wood_dark")
    if books:
        for i in range(n):
            z = 0.075 + i * (h - 0.10) / n
            x = -w / 2 + 0.10
            while x < w / 2 - 0.2:
                bw = _r(rng, 0.02, 0.055)
                bh = _r(rng, 0.16, 0.26)
                bd = _r(rng, 0.14, 0.22)
                if rng.random() < 0.75:
                    mb.box((bw, bd, bh), (x, _r(rng, -0.03, 0.03), z + bh / 2 + 0.015),
                           (0, 0, _r(rng, -0.04, 0.04)),
                           rng.choice(["fabric_navy", "paper_dark", "brick", "paint_charcoal",
                                       "paper", "metal_rust", "plastic_cream"]))
                x += bw + _r(rng, 0.002, 0.02)
                if rng.random() < 0.06:
                    x += 0.10


def wardrobe(mb, w=3.2, h=2.45, d=0.62, doors=3, key="wood_dark"):
    """Floor-to-ceiling wardrobe: carcass, plinth, shadow-gap doors, bar pulls."""
    superbox(mb, (w, d, h - 0.10), (0, 0, (h - 0.10) / 2 + 0.10),
             e=0.10, seg=30, rings=12, key=key)
    mb.box((w - 0.08, d - 0.10, 0.10), (0, 0.02, 0.05), key="metal_black")
    # top shadow gap + cornice
    mb.box((w + 0.02, 0.03, 0.02), (0, -d / 2 - 0.004, h - 0.03), key="metal_black")
    dw = (w - 0.02) / doors
    for i in range(doors):
        x = -w / 2 + dw * (i + 0.5)
        # door slab with a chamfered face
        superbox(mb, (dw - 0.016, 0.030, h - 0.12), (x, -d / 2 - 0.012, h / 2 + 0.01),
                 e=0.12, seg=26, rings=12, key="wood_walnut")
        # recessed centre panel
        mb.box((dw - 0.10, 0.008, h - 0.28), (x, -d / 2 - 0.028, h / 2 + 0.01),
               key="wood_dark")
        # vertical bar handle
        mb.cyl(0.0075, 0.34, (x + dw / 2 - 0.055, -d / 2 - 0.045, 1.15), seg=10,
               key="metal_brushed")
        for dz in (-0.17, 0.17):
            mb.cyl(0.005, 0.022, (x + dw / 2 - 0.055, -d / 2 - 0.033, 1.15 + dz),
                   rot=(math.pi / 2, 0, 0), seg=8, key="metal_brushed")
        # hinge line
        mb.box((0.004, 0.006, h - 0.16), (x - dw / 2 + 0.012, -d / 2 - 0.026, h / 2),
               key="metal_black")
    # interior LED line visible through the gap
    mb.box((w - 0.1, 0.02, 0.012), (0, -d / 2 + 0.02, h - 0.10), key="neon_strip_cool")


def bed(mb, w=1.8, l=2.1, h=0.52, pillows=2, key_duvet="fabric_cream",
        key_frame="wood_walnut", headboard=1.10):
    """Upholstered platform bed: rounded frame, thick mattress, duvet, pillows."""
    # platform frame with a soft edge
    superbox(mb, (l + 0.09, w + 0.09, 0.26), (0, 0, 0.18),
             e=0.20, seg=30, rings=12, key=key_frame)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.026, 0.075, (sx * (l / 2 - 0.03), sy * (w / 2 - 0.03), 0.04),
                   seg=12, key="metal_black")
    # headboard: padded panel with a brass cap rail
    superbox(mb, (0.13, w + 0.16, headboard), (-l / 2 - 0.045, 0, headboard / 2 + 0.11),
             e=0.22, seg=26, rings=16, key=key_frame)
    superbox(mb, (0.15, w + 0.18, 0.05), (-l / 2 - 0.045, 0, headboard + 0.13),
             e=0.30, seg=24, rings=8, key="metal_gold")
    # mattress
    superbox(mb, (l, w, 0.26), (0, 0, 0.42), e=0.24, seg=32, rings=14,
             key="fabric_cream")
    # duvet: a soft slab with a rolled top edge and a slight overhang
    superbox(mb, (l - 0.14, w + 0.14, 0.15), (0.06, 0, 0.545),
             e=0.26, seg=40, rings=18, key=key_duvet, wrinkle=0.011, seed=2.2)
    superbox(mb, (0.42, w + 0.16, 0.10), (-l / 2 + 0.30, 0, 0.575),
             e=0.40, seg=28, rings=12, key="fabric_cream")
    superbox(mb, (l - 0.60, w + 0.06, 0.08), (0.34, 0, 0.595),
             e=0.34, seg=30, rings=12, key=key_duvet)
    # pillows, leaning on the headboard
    for i in range(pillows):
        y = (i - (pillows - 1) / 2) * (w / pillows)
        superbox(mb, (0.30, w / pillows - 0.10, 0.17), (-l / 2 + 0.24, y, 0.645),
                 e=0.55, seg=30, rings=16, key="fabric_cream", rot=(0, 0.30, 0),
                 wrinkle=0.0075, seed=i * 4.1 + 0.7)
    superbox(mb, (0.19, 0.46, 0.13), (-l / 2 + 0.44, 0.12, 0.66),
             e=0.60, seg=24, rings=12, key="fabric_navy", rot=(0, 0.36, 0.16))
    # throw over the foot of the bed, draped down the side
    superbox(mb, (0.46, w + 0.20, 0.035), (l / 2 - 0.40, 0, 0.60),
             e=0.30, seg=30, rings=10, key="fabric_navy", wrinkle=0.008, seed=6.1)
    superbox(mb, (0.035, w + 0.20, 0.16), (l / 2 - 0.185, 0, 0.52),
             e=0.35, seg=22, rings=10, key="fabric_navy")


def nightstand(mb, w=0.48, d=0.42, h=0.52):
    mb.box((w, d, h - 0.06), (0, 0, (h - 0.06) / 2 + 0.06), key="wood_walnut")
    mb.box((w - 0.02, d - 0.02, 0.04), (0, 0, h + 0.02), key="metal_black")
    for i in range(2):
        mb.box((w - 0.06, 0.015, 0.03), (0, -d / 2 - 0.008, 0.20 + i * 0.18), key="metal_gold")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.015, 0.06, (sx * (w / 2 - 0.05), sy * (d / 2 - 0.05), 0.03), seg=8, key="metal_black")


def desk(mb, w=1.7, d=0.72, h=0.74, key_top="wood_dark", key_leg="metal_black"):
    mb.box((w, d, 0.04), (0, 0, h), key=key_top)
    for sx in (-1, 1):
        mb.box((0.04, 0.04, h), (sx * (w / 2 - 0.04), -d / 2 + 0.06, h / 2), key=key_leg)
        mb.box((0.04, 0.04, h), (sx * (w / 2 - 0.04), d / 2 - 0.06, h / 2), key=key_leg)
        mb.box((0.04, d - 0.1, 0.03), (sx * (w / 2 - 0.04), 0, 0.30), key=key_leg)
    mb.box((w - 0.12, d - 0.12, 0.02), (0, 0, h - 0.03), key=key_leg)
    # cable tray + cables
    mb.box((w - 0.4, 0.10, 0.05), (0, d / 2 - 0.12, h - 0.12), key="metal_steel")


def monitor(mb, w=0.62, h=0.36, stand=True, key_frame="plastic_black", tilt=0.0):
    mb.box((w, 0.018, h), (0, 0, 0.0), (tilt, 0, 0), key_frame)
    mb.box((w - 0.02, 0.004, h - 0.02), (0, -0.012, 0.0), (tilt, 0, 0), "screen_ui")
    if stand:
        mb.box((0.05, 0.05, 0.18), (0, 0.05, -h / 2 - 0.08), key=key_frame)
        mb.box((0.22, 0.14, 0.012), (0, 0.06, -h / 2 - 0.17), key=key_frame)


def pc_tower(mb, w=0.22, d=0.46, h=0.46):
    mb.box((w, d, h), (0, 0, h / 2), key="metal_black")
    mb.box((w - 0.01, d - 0.02, 0.01), (0, 0, h + 0.005), key="tech_panel")
    for i in range(3):
        mb.cyl(0.055, 0.012, (-w / 2 - 0.002, -0.12 + i * 0.12, h * 0.55), rot=(0, math.pi / 2, 0),
               seg=20, key="neon_grille")
    mb.box((0.02, 0.10, 0.30), (w / 2 - 0.005, 0.10, h * 0.5), key="circuit")


# ---------------------------------------------------------------------------
# lighting fixtures
# ---------------------------------------------------------------------------


def floor_lamp(mb, h=1.55, r=0.20, key="metal_black"):
    """Drum-shade floor lamp: weighted base, slim stem, fabric shade with diffuser."""
    lathe(mb, [(0.0, 0.0), (r * 0.62, 0.0), (r * 0.66, 0.006), (r * 0.60, 0.016),
               (r * 0.24, 0.030), (0.0, 0.032)], seg=36, key=key)
    mb.cyl(0.013, h - 0.05, (0, 0, h / 2), seg=14, key=key, r2=0.010)
    mb.cyl(0.022, 0.03, (0, 0, h - 0.01), seg=16, key=key)
    # shade: slight barrel with a rolled top and bottom edge
    lathe(mb, [(r * 0.86, h + 0.01), (r, h + 0.03), (r * 1.02, h + 0.13),
               (r, h + 0.23), (r * 0.90, h + 0.25), (r * 0.87, h + 0.245),
               (r * 0.96, h + 0.22), (r * 0.98, h + 0.13), (r * 0.96, h + 0.04),
               (r * 0.84, h + 0.012), (0.0, h + 0.012)], seg=40, key="fabric_cream")
    # diffuser disc under the shade
    lathe(mb, [(0.0, h + 0.015), (r * 0.80, h + 0.016), (0.0, h + 0.018)],
          seg=28, key="lamp_bulb")
    mb.sphere(0.030, (0, 0, h + 0.12), seg=12, rings=8, key="lamp_bulb")


def pendant(mb, drop=1.1, r=0.18, key="metal_black", warm=True):
    """Cone pendant: ceiling rose, cord, spun shade, reflector and bulb."""
    lathe(mb, [(0.0, 0.0), (0.045, 0.0), (0.048, 0.010), (0.040, 0.018),
               (0.0, 0.020)], seg=24, key=key)
    mb.cyl(0.0055, drop, (0, 0, -drop / 2), seg=8, key="metal_black")
    lathe(mb, [(r * 1.00, -drop - 0.20), (r * 1.01, -drop - 0.19),
               (r * 0.92, -drop - 0.06), (r * 0.56, -drop + 0.02),
               (r * 0.50, -drop + 0.02), (r * 0.86, -drop - 0.07),
               (r * 0.95, -drop - 0.19), (0.0, -drop - 0.19)],
          seg=40, key=key)
    lathe(mb, [(0.0, -drop - 0.175), (r * 0.80, -drop - 0.175),
               (0.0, -drop - 0.16)], seg=30,
          key="lamp_bulb" if warm else "neon_white")
    mb.sphere(0.034, (0, 0, -drop - 0.11), seg=14, rings=10, key="lamp_bulb" if warm else "neon_white")
    mb.cyl(0.012, 0.05, (0, 0, -drop + 0.015), seg=10, key=key)


def track_light(mb, length=1.6, n=3):
    mb.box((length, 0.045, 0.045), (0, 0, -0.02), key="metal_black")
    for i in range(n):
        x = -length / 2 + length * (i + 0.5) / n
        mb.cyl(0.045, 0.11, (x, 0, -0.10), seg=14, key="metal_black", r2=0.052)
        mb.disc(0.042, (x, 0, -0.156), rot=(math.pi, 0, 0), seg=14, key="lamp_bulb")


def led_strip(mb, p0, p1, key="neon_strip_warm", w=0.018):
    p0, p1 = cy.Vector(p0), cy.Vector(p1)
    d = p1 - p0
    ln = d.length
    if ln < 1e-6:
        return
    c = (p0 + p1) / 2
    ang = math.atan2(d.y, d.x)
    mb.box((ln, w, w), tuple(c), (0, 0, ang), key=key)


# ---------------------------------------------------------------------------
# plants
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# high-detail primitives
# ---------------------------------------------------------------------------
# Everything below builds real, curved, closed geometry instead of single
# quads: superellipsoids for soft goods, lathed profiles for vessels, and
# swept blades for foliage.  They are the difference between "blocked out" and
# "modelled", so the segment counts are deliberately generous.


def _sup(w, m):
    c = math.cos(w)
    return math.copysign(abs(c) ** m, c) if c else 0.0


def _sup_s(w, m):
    s = math.sin(w)
    return math.copysign(abs(s) ** m, s) if s else 0.0


def _wnoise(x, y, z, seed=0.0):
    """Cheap smooth 3-octave value noise in [-1, 1]; used for fabric crumple."""
    v = 0.0
    for k, (f, a) in enumerate(((3.1, 1.0), (7.3, 0.48), (15.7, 0.22))):
        v += a * (math.sin(x * f + seed * 1.7 + k) * math.sin(y * f * 0.93 + seed * 2.3)
                  * math.sin(z * f * 1.11 + seed * 3.1))
    return v / 1.7


def superbox(mb, size, loc=(0, 0, 0), e=0.35, seg=24, rings=14, key="fabric",
             rot=None, e2=None, wrinkle=0.0, seed=0.0, wfreq=3.2):
    """Superellipsoid: e=1 is an ellipsoid, e->0 approaches a box.

    Used for every soft good: cushions, pillows, mattresses, duvets, bolsters.
    wrinkle>0 adds smooth noise crumple along the surface normal (fabric).
    """
    from mathutils import Vector

    a, b, c = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    e2 = e if e2 is None else e2
    verts = [(0.0, 0.0, -c)]
    for i in range(1, rings):
        v = -math.pi * 0.5 + math.pi * i / rings
        cv = _sup(v, e)
        sv = _sup_s(v, e)
        for k in range(seg):
            u = -math.pi + 2.0 * math.pi * k / seg
            verts.append((a * cv * _sup(u, e2), b * cv * _sup_s(u, e2), c * sv))
    verts.append((0.0, 0.0, c))
    faces = []
    for k in range(seg):
        faces.append((0, 1 + (k + 1) % seg, 1 + k))
    for i in range(rings - 2):
        base = 1 + i * seg
        nxt = base + seg
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((base + k, base + k2, nxt + k2, nxt + k))
    top = len(verts) - 1
    base = 1 + (rings - 2) * seg
    for k in range(seg):
        faces.append((base + k, base + (k + 1) % seg, top))
    if wrinkle:
        out = []
        for (x, y, z) in verts:
            nx = x / a if a > 1e-9 else 0.0
            ny = y / b if b > 1e-9 else 0.0
            nz = z / c if c > 1e-9 else 0.0
            n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            amp = wrinkle * _wnoise(nx * wfreq, ny * wfreq, nz * wfreq, seed)
            out.append((x + nx / n * amp, y + ny / n * amp, z + nz / n * amp))
        verts = out
    if rot is not None:
        M = cy.rot_matrix(rot)
        verts = [tuple(M @ Vector(p) + Vector(loc)) for p in verts]
    else:
        verts = [(p[0] + loc[0], p[1] + loc[1], p[2] + loc[2]) for p in verts]
    mb.add(verts, faces, key)


def lathe(mb, profile, loc=(0, 0, 0), seg=40, key="ceramic_white", rot=None,
          smooth_caps=True):
    """Surface of revolution from an (r, z) profile, bottom to top.

    r == 0 at either end closes that end with a fan, so a vessel is a single
    closed solid (outside wall, rim, inside wall, floor).
    """
    verts = []
    rings = []
    for (r, z) in profile:
        if r <= 1e-6:
            verts.append((0.0, 0.0, z))
            rings.append([len(verts) - 1])
        else:
            idx = []
            for k in range(seg):
                a = 2.0 * math.pi * k / seg
                verts.append((r * math.cos(a), r * math.sin(a), z))
                idx.append(len(verts) - 1)
            rings.append(idx)
    faces = []
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for k in range(seg):
                faces.append((a[0], b[(k + 1) % seg], b[k]))
        elif len(b) == 1:
            for k in range(seg):
                faces.append((a[k], a[(k + 1) % seg], b[0]))
        else:
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((a[k], a[k2], b[k2], b[k]))
    M = cy.rot_matrix(rot) if rot is not None else None
    if M is not None:
        verts = [tuple(M @ cy.Vector(p) + cy.Vector(loc)) for p in verts]
    else:
        verts = [(p[0] + loc[0], p[1] + loc[1], p[2] + loc[2]) for p in verts]
    mb.add(verts, faces, key)


def blade(mb, base, az, length, width, rise=0.10, droop=0.05, twist=0.0,
          fold=0.30, key="plant_green", segs=10, wsegs=4, thick=0.0035,
          notches=0, notch_cut=0.55, curl=0.0, ribs=0, rib_amp=0.0020,
          undulate=0.0, tip_curl=0.0):
    """A real leaf: swept spine, tapered width, V-fold, closed with thickness.

    notches>0 cuts slits in from the margin (monstera-style fenestration).
    """
    from mathutils import Vector, Quaternion

    p0 = Vector(base)
    dx, dy = math.cos(az), math.sin(az)
    p1 = p0 + Vector((dx, dy, 0.0)) * (length * 0.40) + Vector((0.0, 0.0, rise * 0.80))
    p2 = p0 + Vector((dx, dy, 0.0)) * length + Vector((0.0, 0.0, rise - droop))
    side0 = Vector((-dy, dx, 0.0))

    spines = []
    sides = []
    widths = []
    for i in range(segs + 1):
        t = i / segs
        p = p0 * ((1 - t) ** 2) + p1 * (2 * (1 - t) * t) + p2 * (t * t)
        tan = (p1 - p0) * (2 * (1 - t)) + (p2 - p1) * (2 * t)
        if tan.length < 1e-9:
            tan = Vector((0, 0, 1))
        tan.normalize()
        sd = side0.copy()
        if abs(twist) > 1e-9:
            sd = Quaternion(tan, twist * t) @ sd
        # width profile: narrow at the base, widest around 35 %, pointed tip
        w = width * (math.sin(math.pi * min(1.0, t ** 0.62)) ** 0.75)
        if notches and 0.25 < t < 0.92:
            idx = int(round(t * segs))
            if idx % 3 == 1:
                w *= notch_cut
        spines.append(p)
        sides.append(sd)
        widths.append(max(0.002, w))

    top, bot = [], []
    for i in range(segs + 1):
        p, sd, w = spines[i], sides[i], widths[i]
        tnorm = ((p1 - p0) * (2 * (1 - i / segs)) + (p2 - p1) * (2 * i / segs))
        tnorm = tnorm.normalized() if tnorm.length > 1e-9 else Vector((0, 0, 1))
        up = sd.cross(tnorm).normalized()
        if up.z < 0:
            up = -up
        for j in range(wsegs + 1):
            u = -1.0 + 2.0 * j / wsegs
            lift = fold * w * (abs(u) ** 1.7) + curl * w * (u * u)
            if ribs:
                ph = (t * ribs) % 1.0
                rib = math.exp(-(((ph - 0.5) / 0.17) ** 2)) + \
                    math.exp(-(((ph + 0.5) / 0.17) ** 2))
                lift += rib_amp * rib * (0.20 + abs(u)) * (1.0 - 0.55 * t)
            if undulate:
                lift += undulate * math.sin(t * 15.7 + u * 2.4) * (1.0 - abs(u)) * w
            if tip_curl:
                lift += tip_curl * w * (t ** 3) * (1.0 - abs(u))
            ptop = p + sd * (w * u) + up * lift
            top.append(ptop)
            bot.append(ptop - up * thick)

    def idx(i, j):
        return i * (wsegs + 1) + j

    n = len(top)
    faces = []
    for i in range(segs):
        for j in range(wsegs):
            a, b = idx(i, j), idx(i, j + 1)
            c, d = idx(i + 1, j + 1), idx(i + 1, j)
            faces.append((a, b, c, d))
            faces.append((n + d, n + c, n + b, n + a))
    for i in range(segs):  # side walls
        faces.append((idx(i, 0), idx(i + 1, 0), n + idx(i + 1, 0), n + idx(i, 0)))
        faces.append((n + idx(i, wsegs), n + idx(i + 1, wsegs),
                      idx(i + 1, wsegs), idx(i, wsegs)))
    for j in range(wsegs):  # base and tip caps
        faces.append((idx(0, j + 1), idx(0, j), n + idx(0, j), n + idx(0, j + 1)))
        faces.append((idx(segs, j), idx(segs, j + 1),
                      n + idx(segs, j + 1), n + idx(segs, j)))
    verts = [tuple(v) for v in top] + [tuple(v) for v in bot]
    mb.add(verts, faces, key)


def stem(mb, pts, r=0.006, key="plant_green_dark", seg=6, taper=0.55):
    """Tapered curved stem built as a swept tube."""
    from mathutils import Vector

    P = [Vector(p) for p in pts]
    verts, rings = [], []
    for i, p in enumerate(P):
        if i == 0:
            d = P[1] - P[0]
        elif i == len(P) - 1:
            d = P[-1] - P[-2]
        else:
            d = P[i + 1] - P[i - 1]
        d = d.normalized() if d.length > 1e-9 else Vector((0, 0, 1))
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        sd = d.cross(up).normalized()
        u2 = sd.cross(d).normalized()
        rr = r * (1.0 - taper * i / max(1, len(P) - 1))
        idx = []
        for k in range(seg):
            a = 2.0 * math.pi * k / seg
            verts.append(tuple(p + sd * (rr * math.cos(a)) + u2 * (rr * math.sin(a))))
            idx.append(len(verts) - 1)
        rings.append(idx)
    faces = []
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((a[k], a[k2], b[k2], b[k]))
    mb.add(verts, faces, key)


# ---------------------------------------------------------------------------
# foliage
# ---------------------------------------------------------------------------


def plant_pot(mb, r=0.22, h=0.32, key="ceramic_white"):
    """Tapered pot with a foot ring, a rolled rim and a soil surface."""
    prof = [(0.0, 0.0), (r * 0.58, 0.0), (r * 0.60, 0.010),
            (r * 0.74, 0.030), (r * 0.86, h * 0.55), (r * 0.97, h * 0.96),
            (r * 1.00, h), (r * 0.955, h * 1.005), (r * 0.90, h),
            (r * 0.885, h * 0.90), (r * 0.80, h * 0.55), (r * 0.0, h * 0.52)]
    lathe(mb, prof, seg=44, key=key)
    # soil mound sitting inside the rim
    lathe(mb, [(0.0, h * 0.90), (r * 0.50, h * 0.895), (r * 0.80, h * 0.885),
               (r * 0.862, h * 0.905), (r * 0.0, h * 0.93)],
          seg=36, key="soil")
    # a few pebbles on the soil
    rr = random.Random(int(r * 9770))
    for i in range(7):
        a = rr.random() * 6.283
        rad = rr.uniform(0.05, 0.66) * r
        blade(mb, (math.cos(a) * rad, math.sin(a) * rad, h * 0.915),
              a, rr.uniform(0.012, 0.028), rr.uniform(0.010, 0.020),
              rise=0.004, fold=0.9, key="stone_dark", segs=4, wsegs=3, thick=0.004)


def plant_monstera(mb, rng=None, n=9, scale=1.0, pot_r=0.24, pot_h=0.34):
    """Monstera: arching petioles, fenestrated heart leaves, layered canopy."""
    rng = rng or random.Random(3)
    plant_pot(mb, pot_r, pot_h, "ceramic_white")
    for i in range(n):
        a = i * 2.399 + 0.4
        ln = _r(rng, 0.16, 0.34) * scale
        hh = _r(rng, 0.34, 0.92) * scale
        x0, y0 = math.cos(a) * pot_r * 0.22, math.sin(a) * pot_r * 0.22
        z0 = pot_h * 0.90
        # petiole leaves the stem, arcs out then up
        mid = (x0 + math.cos(a) * ln * 0.42, y0 + math.sin(a) * ln * 0.42, z0 + hh * 0.62)
        tip = (x0 + math.cos(a) * ln, y0 + math.sin(a) * ln, z0 + hh)
        stem(mb, [(x0, y0, z0), (x0 + math.cos(a) * ln * 0.12, y0 + math.sin(a) * ln * 0.12,
                                z0 + hh * 0.18), mid, tip],
             r=0.0085 * scale, key="plant_green_dark", seg=7)
        # leaf: broad, drooping, with marginal slits
        lw = _r(rng, 0.10, 0.17) * scale
        ll = _r(rng, 0.17, 0.27) * scale
        az = a + _r(rng, -0.30, 0.30)
        blade(mb, tip, az, ll, lw,
              rise=_r(rng, 0.01, 0.06), droop=_r(rng, 0.06, 0.16),
              twist=_r(rng, -0.30, 0.30), fold=0.30,
              key="plant_green", segs=12, wsegs=5, thick=0.0042,
              notches=1, notch_cut=0.52)
    # young unfurled leaf
    if n > 4:
        stem(mb, [(0.0, 0.0, pot_h * 0.9), (0.02, -0.02, pot_h * 0.9 + 0.16 * scale),
                  (0.03, -0.03, pot_h * 0.9 + 0.30 * scale)],
             r=0.006 * scale, key="plant_green_dark", seg=6)
        blade(mb, (0.03, -0.03, pot_h * 0.9 + 0.30 * scale), 1.57,
              0.09 * scale, 0.035 * scale, rise=0.05, droop=0.0,
              fold=0.6, key="plant_green", segs=8, wsegs=3, thick=0.003)


def plant_bamboo(mb, rng=None, n=7, scale=1.0):
    """Bamboo: square planter, culms with node rings, leaf fans."""
    rng = rng or random.Random(11)
    w = 0.42 * scale
    lathe(mb, [(0.0, 0.0), (w * 0.5, 0.0), (w * 0.5, 0.012), (w * 0.52, 0.30),
               (w * 0.50, 0.42), (w * 0.455, 0.44), (w * 0.44, 0.40),
               (w * 0.0, 0.40)], seg=4, key="concrete_raw")
    lathe(mb, [(0.0, 0.395), (w * 0.44, 0.395), (w * 0.0, 0.405)],
          seg=4, key="soil")
    for i in range(n):
        a = rng.random() * 6.283
        rr = _r(rng, 0.02, 0.15) * scale
        x, y = math.cos(a) * rr, math.sin(a) * rr
        hh = _r(rng, 0.85, 1.75) * scale
        lean = _r(rng, -0.10, 0.10)
        r0 = _r(rng, 0.008, 0.013) * scale
        z0 = 0.40
        seg_h = 5
        pts = []
        for s in range(seg_h + 1):
            t = s / seg_h
            pts.append((x + lean * t * t * hh * 0.5, y + lean * 0.6 * t * t * hh * 0.3,
                        z0 + hh * t))
        stem(mb, pts, r=r0, key="plant_bamboo_stem", seg=8, taper=0.45)
        # node rings
        for s in range(1, seg_h):
            t = s / seg_h
            px, py, pz = x + lean * t * t * hh * 0.5, y + lean * 0.6 * t * t * hh * 0.3, z0 + hh * t
            lathe(mb, [(r0 * 1.02, -0.006), (r0 * 1.35, -0.002), (r0 * 1.35, 0.004),
                       (r0 * 1.02, 0.008)], loc=(px, py, pz), seg=10,
                  key="plant_bamboo_stem")
        # leaf fans near the top
        for k in range(7):
            t = _r(rng, 0.55, 1.0)
            px = x + lean * t * t * hh * 0.5
            py = y + lean * 0.6 * t * t * hh * 0.3
            pz = z0 + hh * t
            ang = rng.random() * 6.283
            blade(mb, (px, py, pz), ang,
                  _r(rng, 0.10, 0.19) * scale, _r(rng, 0.016, 0.028) * scale,
                  rise=_r(rng, 0.01, 0.05), droop=_r(rng, 0.05, 0.11),
                  fold=0.45, key="plant_green", segs=7, wsegs=3, thick=0.0022)


def plant_snake(mb, rng=None):
    """Snake plant: stiff upright blades with a fold, twist and mottling."""
    rng = rng or random.Random(21)
    plant_pot(mb, 0.16, 0.26, "concrete_raw")
    for i in range(13):
        a = rng.random() * 6.283
        rr = _r(rng, 0.0, 0.095)
        hh = _r(rng, 0.28, 0.64)
        lean = _r(rng, 0.05, 0.20)
        x, y = math.cos(a) * rr, math.sin(a) * rr
        az = rng.random() * 6.283
        blade(mb, (x, y, 0.255), az, lean + 0.035, _r(rng, 0.038, 0.058),
              rise=hh, droop=-0.02, twist=_r(rng, -0.9, 0.9), fold=0.42,
              key="plant_green", segs=9, wsegs=4, thick=0.004)


def hanging_plant(mb, rng=None, drop=0.5):
    """Hanging planter with trailing vines and small leaves."""
    rng = rng or random.Random(31)
    lathe(mb, [(0.0, -0.10), (0.055, -0.095), (0.075, -0.06), (0.085, 0.0),
               (0.105, 0.055), (0.13, 0.075), (0.128, 0.078), (0.10, 0.062),
               (0.082, 0.02), (0.0, 0.02)], seg=32, key="ceramic_white")
    lathe(mb, [(0.0, 0.062), (0.095, 0.060), (0.0, 0.070)], seg=24, key="soil")
    # hanger cords
    for k in range(3):
        a = k * 2.094
        px, py = math.cos(a) * 0.115, math.sin(a) * 0.115
        stem(mb, [(px, py, 0.075), (px * 0.75, py * 0.75, 0.30),
                  (px * 0.25, py * 0.25, 0.48)], r=0.0022, key="rope", seg=4)
    for i in range(14):
        a = rng.random() * 6.283
        ln = _r(rng, 0.22, 0.72) * drop / 0.5
        x, y = math.cos(a) * 0.085, math.sin(a) * 0.085
        sag = _r(rng, 0.05, 0.14)
        pts = [(x, y, 0.04),
               (x * 1.9, y * 1.9, -ln * 0.30),
               (x * 2.7 + 0.03, y * 2.7, -ln * 0.68),
               (x * 2.9 + 0.05, y * 2.9, -ln)]
        stem(mb, pts, r=0.0038, key="plant_green_dark", seg=5)
        tip = pts[-1]
        blade(mb, tip, a, _r(rng, 0.045, 0.075), _r(rng, 0.016, 0.028),
              rise=-0.008, droop=_r(rng, 0.02, 0.05), fold=0.5,
              key="plant_green", segs=7, wsegs=3, thick=0.0018)
        for k in range(2):
            t = 0.4 + 0.22 * k
            p = (x * (1 + 2.0 * t), y * (1 + 2.0 * t), -ln * t)
            blade(mb, p, a + 1.6 * (k + 1), _r(rng, 0.035, 0.06),
                  _r(rng, 0.012, 0.022), rise=0.006, droop=0.03, fold=0.5,
                  key="plant_green", segs=6, wsegs=3, thick=0.0016)


# ---------------------------------------------------------------------------
# textiles / surfaces
# ---------------------------------------------------------------------------


def rug(mb, w=4.0, d=2.8, key="rug", thick=0.012, fringe=True):
    mb.box((w, d, thick), (0, 0, thick / 2), key=key)
    if fringe:
        n = int(w / 0.03)
        for i in range(n):
            x = -w / 2 + (i + 0.5) * w / n
            for sy in (-1, 1):
                mb.box((0.008, 0.045, thick * 0.8),
                       (x, sy * (d / 2 + 0.02), thick * 0.4), key="fabric_cream")


def curtain(mb, w=2.4, h=2.7, folds=9, key="curtain", amp=0.055, thick=0.012):
    """Gathered fabric: sinusoidal folds that deepen toward the floor."""
    cols = max(24, folds * 9)
    rows = 9
    off = lambda t, zt: math.sin(t * math.pi * 2.0 * folds) * amp * (0.40 + 0.85 * (1.0 - zt))
    front, back = [], []
    for i in range(cols + 1):
        t = i / cols
        x = (t - 0.5) * w
        frow, brow = [], []
        for j in range(rows + 1):
            zt = j / rows
            z = 0.015 + zt * (h - 0.015)
            # fabric gathers slightly at the top
            y = off(t, zt) * (0.72 + 0.28 * (1.0 - zt))
            frow.append((x, y - thick * 0.5, z))
            brow.append((x, y + thick * 0.5, z))
        front.append(frow)
        back.append(brow)
    verts = []
    for row in front:
        verts.extend(row)
    for row in back:
        verts.extend(row)
    n = len(front) * (rows + 1)
    def fi(i, j):
        return i * (rows + 1) + j
    faces = []
    for i in range(cols):
        for j in range(rows):
            a, b = fi(i, j), fi(i, j + 1)
            c, d = fi(i + 1, j + 1), fi(i + 1, j)
            faces.append((a, b, c, d))
            faces.append((n + d, n + c, n + b, n + a))
    for i in range(cols):
        faces.append((fi(i, 0), fi(i + 1, 0), n + fi(i + 1, 0), n + fi(i, 0)))
        faces.append((n + fi(i, rows), n + fi(i + 1, rows),
                      fi(i + 1, rows), fi(i, rows)))
    for j in range(rows):
        faces.append((fi(0, j + 1), fi(0, j), n + fi(0, j), n + fi(0, j + 1)))
        faces.append((n + fi(cols, j), n + fi(cols, j + 1),
                      fi(cols, j + 1), fi(cols, j)))
    mb.add(verts, faces, key)


def blind(mb, w=2.4, h=2.4, slats=26, key="plastic_cream", tilt=0.5):
    mb.box((w, 0.05, 0.06), (0, 0, h), key="metal_black")
    for i in range(slats):
        z = h - 0.12 - i * (h - 0.2) / slats
        mb.box((w, 0.055, 0.008), (0, 0, z), (tilt * 0.5, 0, 0), key=key)


# ---------------------------------------------------------------------------
# tech / appliances
# ---------------------------------------------------------------------------


def ac_indoor(mb, w=0.90, h=0.28, d=0.20):
    mb.box((w, d, h), (0, 0, h / 2), key="plastic_white")
    mb.box((w - 0.06, 0.02, 0.05), (0, -d / 2 - 0.005, 0.03), key="plastic_black")
    for i in range(14):
        mb.box((w - 0.12, 0.01, 0.008), (0, -d / 2 - 0.006, 0.10 + i * 0.012), key="plastic_black")
    mb.box((0.06, 0.004, 0.02), (w / 2 - 0.10, -d / 2 - 0.008, 0.20), key="neon_strip_cool")


def ac_outdoor(mb, w=1.0, h=0.72, d=0.38):
    mb.box((w, d, h), (0, 0, h / 2), key="metal_steel")
    mb.cyl(0.25, 0.03, (0.05, 0, h / 2), rot=(math.pi / 2, 0, 0), seg=26, key="metal_black")
    for i in range(4):
        mb.box((0.04, 0.02, 0.42), (0.05 - 0.2 + i * 0.13, -0.02, h / 2), key="metal_black")
    for sx in (-1, 1):
        mb.box((0.03, 0.5, 0.03), (sx * (w / 2 + 0.15), 0, 0.06), key="metal_steel")


def kitchen_run(mb, length=3.4, depth=0.63, height=0.90, sink_at=None, hob_at=None,
                key="plastic_black", top_key="marble"):
    """Base cabinets + worktop + backsplash, running along +X from x=0."""
    # carcass with a recessed plinth
    superbox(mb, (length, depth - 0.06, height - 0.10), (length / 2, 0.02, (height - 0.10) / 2 + 0.10),
             e=0.08, seg=28, rings=10, key=key)
    mb.box((length - 0.06, depth - 0.20, 0.10), (length / 2, -0.02, 0.05), key="metal_black")
    # worktop with a soft front edge and a slight overhang
    superbox(mb, (length + 0.02, depth + 0.03, 0.045), (length / 2, 0.008, height + 0.022),
             e=0.14, seg=30, rings=10, key=top_key)
    # upstand
    mb.box((length, 0.018, 0.055), (length / 2, -depth / 2 + 0.015, height + 0.070), key=top_key)
    # doors: shadow gaps, recessed panel, bar handle
    n = max(3, int(length / 0.6))
    dw = length / n
    for i in range(n):
        x = dw * (i + 0.5)
        superbox(mb, (dw - 0.014, 0.024, height - 0.24), (x, -depth / 2 - 0.008,
                                                          (height - 0.24) / 2 + 0.13),
                 e=0.10, seg=22, rings=10, key=key)
        mb.box((dw - 0.09, 0.006, height - 0.34), (x, -depth / 2 - 0.020,
                                                   (height - 0.24) / 2 + 0.13), key="metal_black")
        mb.cyl(0.0065, dw * 0.52, (x, -depth / 2 - 0.034, height - 0.115),
               rot=(0, math.pi / 2, 0), seg=10, key="metal_brushed")
        for dx in (-dw * 0.26, dw * 0.26):
            mb.cyl(0.0045, 0.016, (x + dx, -depth / 2 - 0.026, height - 0.115),
                   rot=(math.pi / 2, 0, 0), seg=8, key="metal_brushed")
    # backsplash tiles (two courses with a grout shadow line)
    mb.box((length, 0.020, 0.55), (length / 2, -depth / 2 + 0.010, height + 0.30), key="tile_bath")
    mb.box((length, 0.004, 0.006), (length / 2, -depth / 2 - 0.002, height + 0.30), key="grout")
    # under-cabinet LED
    mb.box((length - 0.1, 0.02, 0.008), (length / 2, -depth / 2 + 0.10, height + 0.055),
           key="neon_strip_warm")
    if sink_at is not None:
        x = sink_at
        # undermount basin with a rounded rim
        superbox(mb, (0.64, 0.44, 0.020), (x, 0.02, height - 0.058), e=0.18, seg=26, rings=8,
                 key="metal_steel")
        superbox(mb, (0.56, 0.36, 0.17), (x, 0.02, height - 0.075), e=0.22, seg=26, rings=10,
                 key="metal_dark")
        # gooseneck tap
        mb.cyl(0.020, 0.045, (x, 0.20, height + 0.045), seg=16, key="metal_chrome")
        stem(mb, [(x, 0.20, height + 0.065), (x, 0.20, height + 0.26),
                  (x, 0.16, height + 0.335), (x, 0.075, height + 0.345),
                  (x, 0.030, height + 0.315)],
             r=0.014, key="metal_chrome", seg=12, taper=0.25)
        mb.cyl(0.006, 0.030, (x, 0.032, height + 0.298), seg=10, key="metal_chrome")
    if hob_at is not None:
        x = hob_at
        mb.box((0.60, 0.46, 0.008), (x, 0.0, height + 0.044), key="glass_black")
        for i, (dx, dy) in enumerate([(-0.14, -0.10), (0.14, -0.10), (-0.14, 0.10), (0.14, 0.10)]):
            mb.cyl(0.075, 0.004, (x + dx, dy, height + 0.050), seg=22, key="metal_dark")
            if i == 0:
                mb.cyl(0.06, 0.003, (x + dx, dy, height + 0.053), seg=20, key="neon_red")


def upper_cabinets(mb, length=3.2, z0=1.50, z1=2.35, depth=0.34, key="wood_dark"):
    mb.box((length, depth, z1 - z0), (length / 2, 0, (z0 + z1) / 2), key=key)
    n = max(2, int(length / 0.6))
    for i in range(n):
        x = length * (i + 0.5) / n
        mb.box((length / n - 0.01, 0.016, z1 - z0 - 0.02),
               (x, -depth / 2 - 0.01, (z0 + z1) / 2), key="wood_walnut")
        mb.box((0.012, 0.02, 0.14), (x + (length / n) / 2 - 0.05, -depth / 2 - 0.022, z0 + 0.14),
               key="metal_gold")


def fridge(mb, w=0.75, d=0.68, h=2.02):
    mb.box((w, d, h), (0, 0, h / 2), key="metal_steel")
    mb.box((w + 0.01, 0.02, 0.012), (0, -d / 2 - 0.01, h * 0.62), key="metal_black")
    for sx in (-1, 1):
        mb.box((0.012, 0.03, 0.55), (sx * 0.06, -d / 2 - 0.02, h * 0.78), key="metal_black")
    # magnets / notes
    for i in range(6):
        mb.box((0.05, 0.004, 0.05), (-0.22 + i * 0.09, -d / 2 - 0.004, 1.35 + (i % 3) * 0.12),
               (0, 0, i * 0.2), ["paper", "neon_magenta", "neon_cyan", "neon_amber"][i % 4])
    mb.box((0.18, 0.004, 0.24), (0.20, -d / 2 - 0.004, 1.55), (0, 0, 0.05), "paper")


def range_hood(mb, w=0.9, d=0.5, h=0.20):
    mb.box((w, d, h), (0, 0, h / 2), key="metal_steel")
    mb.box((w - 0.04, d - 0.04, 0.02), (0, 0, 0.01), key="metal_black")
    mb.box((0.02, d - 0.06, 0.03), (0, 0, 0.02), key="neon_strip_warm")


def washer(mb, w=0.60, d=0.60, h=0.85):
    mb.box((w, d, h), (0, 0, h / 2), key="plastic_white")
    mb.cyl(0.20, 0.02, (0, -d / 2 - 0.005, h * 0.52), rot=(math.pi / 2, 0, 0), seg=26,
           key="glass_black")
    mb.box((w - 0.04, 0.01, 0.10), (0, -d / 2 - 0.006, h - 0.08), key="plastic_black")
    for i in range(4):
        mb.cyl(0.012, 0.006, (-0.18 + i * 0.12, -d / 2 - 0.008, h - 0.08), rot=(math.pi / 2, 0, 0),
               seg=8, key="neon_strip_cool")


def server_rack(mb, w=0.6, d=0.7, h=1.2):
    mb.box((w, d, h), (0, 0, h / 2), key="metal_black")
    for i in range(8):
        z = 0.10 + i * (h - 0.14) / 8
        mb.box((w - 0.04, 0.012, (h - 0.14) / 8 - 0.012), (0, -d / 2 - 0.008, z), key="tech_panel")
        mb.box((0.02, 0.006, 0.02), (w / 2 - 0.08, -d / 2 - 0.016, z), key="neon_green" if i % 3 else "neon_red")
    mb.box((w - 0.02, 0.004, 0.01), (0, -d / 2 - 0.012, h - 0.03), key="neon_strip_cool")


def arcade_machine(mb, w=0.78, d=0.82, h=1.78):
    mb.box((w, d, 0.90), (0, 0, 0.45), key="metal_black")
    # angled control panel
    mb.box((w, 0.34, 0.10), (0, -0.24, 0.95), (0.22, 0, 0), "plastic_black")
    mb.box((w, 0.90, 0.82), (0, 0.02, 1.31), (-0.10, 0, 0), "metal_black")
    # screen
    mb.box((w - 0.10, 0.02, 0.52), (0, -0.34, 1.34), (-0.10, 0, 0), "screen_ui")
    # marquee
    mb.box((w - 0.04, 0.06, 0.20), (0, -0.36, 1.80), (-0.10, 0, 0), "neon_grille")
    # joystick + buttons
    mb.cyl(0.012, 0.10, (-0.16, -0.26, 1.02), seg=8, key="metal_steel")
    mb.sphere(0.03, (-0.16, -0.26, 1.08), seg=10, rings=6, key="neon_red")
    for i in range(4):
        mb.cyl(0.022, 0.012, (0.02 + i * 0.07, -0.28, 1.005), rot=(0.22, 0, 0), seg=12,
               key=["neon_cyan", "neon_magenta", "neon_amber", "neon_green"][i])
    # side art
    mb.box((0.006, d - 0.10, 1.6), (w / 2, 0, 0.85), key="holo_panel")
    mb.box((0.006, d - 0.10, 1.6), (-w / 2, 0, 0.85), key="holo_panel")


def tv_panel(mb, w=2.4, h=1.35, z=1.55, key="screen_ui"):
    """Wall panel / TV: rounded chassis, inset screen, side connectors, bracket."""
    superbox(mb, (w + 0.05, 0.055, h + 0.05), (0, 0.02, z), e=0.10, seg=28, rings=10,
             key="metal_black")
    superbox(mb, (w, 0.012, h), (0, -0.014, z), e=0.06, seg=26, rings=8, key=key)
    # thin highlight along the bottom edge and a cable drop
    mb.box((w - 0.10, 0.010, 0.008), (0, -0.020, z - h / 2 + 0.020), key="metal_brushed")
    mb.cyl(0.006, 0.55, (w / 2 - 0.06, 0.045, z - h / 2 - 0.25), seg=8, key="metal_black")
    for i in range(3):
        mb.box((0.030, 0.014, 0.016), (-w / 2 + 0.10 + i * 0.05, -0.028, z - h / 2 + 0.030),
               key="metal_brushed")
    mb.box((0.26, 0.035, 0.26), (0, 0.055, z), key="metal_black")
    mb.box((0.05, 0.10, 0.14), (0, 0.10, z - 0.10), key="metal_black")


def holo_emitter(mb, r=0.14, h=0.06):
    mb.cyl(r, h, (0, 0, h / 2), seg=26, key="metal_chrome")
    mb.cyl(r * 0.7, 0.004, (0, 0, h + 0.004), seg=26, key="holo_cyan")


# ---------------------------------------------------------------------------
# bathroom
# ---------------------------------------------------------------------------


def toilet(mb, key="ceramic_white"):
    """Wall-faced pan: tapered pedestal, oval bowl, seat, cistern, flush plate."""
    lathe(mb, [(0.0, 0.0), (0.115, 0.0), (0.118, 0.020), (0.100, 0.120),
               (0.128, 0.230), (0.150, 0.320), (0.0, 0.330)], seg=32, key=key)
    superbox(mb, (0.355, 0.50, 0.215), (0, -0.075, 0.375), e=0.52, seg=32, rings=14, key=key)
    # seat ring + lid line
    superbox(mb, (0.365, 0.505, 0.035), (0, -0.075, 0.487), e=0.55, seg=30, rings=8, key=key)
    superbox(mb, (0.250, 0.330, 0.012), (0, -0.115, 0.505), e=0.60, seg=26, rings=6,
             key="rubber")
    # cistern
    superbox(mb, (0.375, 0.170, 0.520), (0, 0.235, 0.560), e=0.30, seg=30, rings=12, key=key)
    mb.box((0.372, 0.006, 0.505), (0, 0.150, 0.560), key="grout")
    mb.cyl(0.048, 0.014, (0, 0.235, 0.826), seg=20, key="metal_chrome")
    mb.box((0.150, 0.010, 0.090), (0, 0.146, 0.700), key="metal_chrome")
    mb.box((0.100, 0.004, 0.045), (0, 0.141, 0.700), key="metal_brushed")


def basin(mb, w=0.9, d=0.48, h=0.86):
    """Vanity: stone top, vessel bowl with a real cavity, tap, drawer fronts."""
    superbox(mb, (w + 0.02, d + 0.02, 0.055), (0, 0, h - 0.027), e=0.16, seg=30, rings=10,
             key="marble")
    superbox(mb, (w - 0.02, d - 0.02, h - 0.10), (0, 0.01, (h - 0.10) / 2),
             e=0.10, seg=26, rings=10, key="wood_dark")
    # two drawer fronts with bar pulls
    for i, dz in enumerate((h * 0.62, h * 0.30)):
        mb.box((w - 0.09, 0.012, h * 0.24), (0, -d / 2 - 0.006, dz), key="wood_walnut")
        mb.cyl(0.0055, w * 0.36, (0, -d / 2 - 0.026, dz + h * 0.085),
               rot=(0, math.pi / 2, 0), seg=10, key="metal_gold")
    # vessel bowl
    br = min(w * 0.42, 0.22)
    lathe(mb, [(0.0, h), (br * 0.55, h), (br * 0.60, h + 0.006), (br * 0.92, h + 0.075),
               (br, h + 0.135), (br * 0.96, h + 0.145), (br * 0.88, h + 0.132),
               (br * 0.80, h + 0.070), (br * 0.50, h + 0.030), (0.0, h + 0.026)],
          seg=40, key="ceramic_white")
    lathe(mb, [(0.0, h + 0.030), (0.018, h + 0.032), (0.020, h + 0.028), (0.0, h + 0.027)],
          seg=16, key="metal_chrome")
    # tall mixer
    mb.cyl(0.021, 0.030, (0, d / 2 - 0.075, h + 0.010), seg=18, key="metal_chrome")
    stem(mb, [(0, d / 2 - 0.075, h + 0.030), (0, d / 2 - 0.075, h + 0.240),
              (0, d / 2 - 0.120, h + 0.300), (0, d / 2 - 0.190, h + 0.295)],
         r=0.0135, key="metal_chrome", seg=12, taper=0.2)
    mb.cyl(0.007, 0.026, (0, d / 2 - 0.190, h + 0.276), seg=10, key="metal_chrome")
    for sx in (-1, 1):
        mb.box((0.010, 0.008, 0.075), (sx * (w / 2 - 0.11), -d / 2 - 0.020, h * 0.62),
               key="metal_gold")


def mirror(mb, w=0.9, h=1.0, z=1.55, frame=True):
    if frame:
        mb.box((w + 0.04, 0.03, h + 0.04), (0, 0, z), key="metal_black")
    mb.box((w, 0.006, h), (0, -0.02, z), key="mirror")
    mb.box((w - 0.06, 0.02, 0.016), (0, -0.03, z + h / 2 - 0.02), key="neon_strip_cool")


def shower(mb, w=0.95, d=1.1, h=2.1):
    mb.box((w, d, 0.05), (0, 0, 0.025), key="tile_bath")
    mb.box((0.02, d, h), (-w / 2, 0, h / 2), key="glass_shower")
    mb.box((w, 0.02, h), (0, -d / 2, h / 2), key="glass_shower")
    mb.box((0.05, 0.05, 0.02), (-w / 2, -d / 2, h), key="metal_steel")
    mb.cyl(0.10, 0.02, (0, 0.2, h - 0.12), rot=(0, 0, 0), seg=20, key="metal_chrome")
    mb.cyl(0.012, 0.9, (0, 0.2, h - 0.12), seg=8, key="metal_chrome")
    mb.box((0.05, 0.03, 0.10), (-w / 2 + 0.02, -d / 2 + 0.10, 1.05), key="metal_chrome")


def bathtub(mb, w=1.66, d=0.78, h=0.56):
    mb.box((w, d, h), (0, 0, h / 2), key="ceramic_white")
    mb.box((w - 0.12, d - 0.12, 0.02), (0, 0, h - 0.02), key="water")
    mb.cyl(0.016, 0.22, (-w / 2 + 0.12, 0, h + 0.10), seg=10, key="metal_chrome")
    mb.tube([(-w / 2 + 0.12, 0, h + 0.20), (-w / 2 + 0.12, -0.06, h + 0.24), (-w / 2 + 0.12, -0.12, h + 0.18)],
            0.014, "metal_chrome", seg=8)
    mb.box((0.05, 0.05, 0.30), (w / 2 - 0.05, 0, h + 0.15), key="metal_chrome")


# ---------------------------------------------------------------------------
# clutter
# ---------------------------------------------------------------------------


def books_stack(mb, n=4, rng=None, w=0.24, d=0.18):
    rng = rng or random.Random(5)
    z = 0.0
    for i in range(n):
        t = _r(rng, 0.02, 0.05)
        mb.box((w + _r(rng, -0.03, 0.03), d, t), (_r(rng, -0.02, 0.02), _r(rng, -0.01, 0.01), z + t / 2),
               (0, 0, _r(rng, -0.25, 0.25)),
               rng.choice(["paper", "fabric_navy", "brick", "paper_dark", "plastic_cream"]))
        z += t


def mug(mb, r=0.042, h=0.10, key="ceramic_white"):
    """Thrown mug: tapered wall, rolled rim, hollow interior, loop handle."""
    lathe(mb, [(0.0, 0.0), (r * 0.80, 0.0), (r * 0.86, 0.004), (r * 0.92, h * 0.30),
               (r, h), (r * 0.96, h * 1.01), (r * 0.88, h), (r * 0.84, h * 0.55),
               (r * 0.76, 0.018), (0.0, 0.016)], seg=30, key=key)
    lathe(mb, [(0.0, 0.055), (r * 0.70, 0.054), (r * 0.74, 0.052), (0.0, 0.051)],
          seg=24, key="water")
    pts = []
    for i in range(9):
        a = -0.35 + math.pi * i / 8
        pts.append((r * 0.92 + math.sin(a) * r * 0.62,
                    math.cos(a) * 0.0,
                    h * 0.50 + math.cos(a) * h * 0.30))
    stem(mb, pts, r=0.0075, key=key, seg=8, taper=0.25)


def bottle(mb, h=0.26, r=0.036, key="glass_black", cap="metal_gold"):
    """Bottle: punt, shoulder curve, neck, collar and cap."""
    lathe(mb, [(0.0, 0.0), (r * 0.62, 0.0), (r * 0.95, 0.006), (r, h * 0.06),
               (r, h * 0.58), (r * 0.96, h * 0.66), (r * 0.70, h * 0.80),
               (r * 0.44, h * 0.88), (r * 0.42, h * 0.96), (r * 0.50, h * 0.985),
               (r * 0.46, h), (0.0, h)], seg=30, key=key)
    lathe(mb, [(r * 0.47, h * 0.965), (r * 0.53, h * 0.985), (r * 0.53, h * 1.035),
               (r * 0.47, h * 1.045), (0.0, h * 1.045)], seg=24, key=cap)
    lathe(mb, [(0.0, h * 0.34), (r * 0.86, h * 0.338), (0.0, h * 0.336)],
          seg=20, key="paper")


def can(mb, r=0.033, h=0.12, key="metal_steel"):
    """Drink can: double seam top and bottom, slight waist."""
    lathe(mb, [(0.0, 0.0), (r * 0.80, 0.0), (r * 0.96, 0.006), (r, 0.012),
               (r * 0.985, h * 0.5), (r, h - 0.012), (r * 0.96, h - 0.004),
               (r * 0.86, h), (r * 0.80, h - 0.004), (0.0, h - 0.004)],
          seg=26, key=key)
    lathe(mb, [(0.0, h - 0.005), (r * 0.62, h - 0.004), (r * 0.66, h + 0.002),
               (r * 0.80, h + 0.001), (0.0, h + 0.001)], seg=22, key="metal_steel")


def bowl(mb, r=0.12, h=0.07, key="ceramic_white"):
    """Shallow bowl: foot ring, flared wall, wall thickness, inner surface."""
    lathe(mb, [(0.0, 0.0), (r * 0.42, 0.0), (r * 0.44, 0.005), (r * 0.40, h * 0.22),
               (r * 0.72, h * 0.62), (r, h), (r * 0.96, h * 1.015),
               (r * 0.90, h), (r * 0.62, h * 0.60), (r * 0.34, h * 0.20),
               (0.0, h * 0.17)], seg=34, key=key)


def pizza_box(mb):
    mb.box((0.36, 0.36, 0.035), (0, 0, 0.018), key="paper")


def takeout_container(mb, w=0.16, d=0.12, h=0.07):
    mb.box((w, d, h), (0, 0, h / 2), key="plastic_white")
    mb.box((w - 0.01, d - 0.01, 0.012), (0, 0, h + 0.006), key="glass_window")


def cable_coil(mb, r=0.09, turns=5):
    for i in range(turns):
        mb.torus if False else None
        ring = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            ring.append((r * math.cos(a), r * math.sin(a), i * 0.012))
        for k in range(16):
            k2 = (k + 1) % 16
            mb.add([ring[k], ring[k2], (ring[k2][0], ring[k2][1], ring[k2][2] + 0.011),
                    (ring[k][0], ring[k][1], ring[k][2] + 0.011)],
                   [(0, 1, 2, 3)], "plastic_black")


def vr_headset(mb):
    mb.box((0.20, 0.12, 0.11), (0, 0, 0.055), key="plastic_black")
    mb.box((0.21, 0.02, 0.05), (0, -0.06, 0.055), key="neon_strip_cool")
    for sx in (-1, 1):
        mb.cyl(0.045, 0.02, (sx * 0.10, -0.056, 0.055), rot=(math.pi / 2, 0, 0), seg=16,
               key="glass_black")


def picture_frame(mb, w=0.5, h=0.65, key="metal_black", art="holo_panel"):
    mb.box((w + 0.04, 0.03, h + 0.04), (0, 0, h / 2), key=key)
    mb.box((w, 0.006, h), (0, -0.02, h / 2), key=art)


def poster(mb, w=0.62, h=0.88, key="screen_ui"):
    mb.box((w, 0.006, h), (0, 0, h / 2), key=key)


def guitar(mb):
    mb.add([(0, -0.10, 0.30), (0.16, -0.12, 0.42), (0.14, -0.10, 0.62),
            (0.02, -0.09, 0.70), (-0.11, -0.10, 0.58), (-0.10, -0.11, 0.40)],
           [(0, 1, 2, 3, 4, 5)], "wood_oak")
    mb.box((0.05, 0.03, 0.55), (0.03, -0.10, 0.98), key="wood_walnut")
    for i in range(6):
        mb.box((0.004, 0.002, 0.55), (0.015 + i * 0.006, -0.085, 0.98), key="metal_steel")


def umbrella_stand(mb):
    mb.cyl(0.10, 0.40, (0, 0, 0.20), seg=18, key="metal_dark")
    for i in range(3):
        mb.cyl(0.014, 0.85, (0.03 * math.cos(i * 2), 0.03 * math.sin(i * 2), 0.60),
               (0.06 * math.cos(i), 0.06 * math.sin(i), 0), seg=8, key="plastic_black")


def box_stack(mb, n=3, rng=None):
    rng = rng or random.Random(9)
    z = 0.0
    for i in range(n):
        w = _r(rng, 0.26, 0.42)
        d = _r(rng, 0.24, 0.36)
        h = _r(rng, 0.16, 0.26)
        mb.box((w, d, h), (_r(rng, -0.05, 0.05), _r(rng, -0.05, 0.05), z + h / 2),
               (0, 0, _r(rng, -0.2, 0.2)), "wood_oak")
        z += h


def shoe_pair(mb, rng=None):
    rng = rng or random.Random(13)
    for sx in (-1, 1):
        mb.box((0.10, 0.27, 0.09), (sx * 0.055, 0, 0.045), (0, 0, _r(rng, -0.2, 0.2)),
               "plastic_black")


def drone_toy(mb):
    mb.box((0.16, 0.16, 0.05), (0, 0, 0.025), key="plastic_black")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl(0.055, 0.006, (sx * 0.10, sy * 0.10, 0.05), seg=14, key="metal_steel")
            mb.box((0.10, 0.02, 0.008), (sx * 0.055, sy * 0.055, 0.032), key="metal_black")
    mb.box((0.02, 0.02, 0.008), (0, -0.09, 0.01), key="neon_red")