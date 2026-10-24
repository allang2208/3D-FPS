"""furn2 -- generation-2 props: extra plant species and micro clutter.

Everything here builds real curved geometry (swept blades, lathed vessels,
wrinkled superellipsoids).  Local convention matches furn: origin at the
resting surface, front facing -Y, Z up.
"""
from __future__ import annotations

import math
import random

import cy_lib as cy
from furn import _r, blade, lathe, plant_pot, stem, superbox


# ---------------------------------------------------------------------------
# plant species
# ---------------------------------------------------------------------------


def plant_fern(mb, rng=None, fronds=9, scale=1.0, pot_r=0.20, pot_h=0.26):
    """Boston fern: arching rachis, pinnae pairs that shrink toward the tip."""
    rng = rng or random.Random(5)
    plant_pot(mb, pot_r, pot_h, "ceramic_white")
    for i in range(fronds):
        a = i * 2.399 + 0.2
        ln = _r(rng, 0.24, 0.44) * scale
        rise = _r(rng, 0.10, 0.30) * scale
        x0 = math.cos(a) * pot_r * 0.28
        y0 = math.sin(a) * pot_r * 0.28
        z0 = pot_h * 0.90
        n = 6
        pts = []
        for s in range(n + 1):
            t = s / n
            pts.append((x0 + math.cos(a) * ln * t,
                        y0 + math.sin(a) * ln * t,
                        z0 + rise * math.sin(t * 1.35) - 0.55 * rise * t * t))
        stem(mb, pts, r=0.0050 * scale, key="plant_green_dark", seg=5, taper=0.65)
        for s in range(1, n + 1):
            t = s / n
            px, py, pz = pts[s]
            sz = scale * (0.024 + 0.052 * math.sin(math.pi * min(1.0, t * 1.06)))
            for side in (-1, 1):
                ang = a + side * (1.20 - 0.40 * t)
                blade(mb, (px, py, pz), ang, sz * 2.1, sz * 0.80,
                      rise=0.010, droop=0.030, fold=0.34, ribs=3, rib_amp=0.0012,
                      key="plant_green", segs=5, wsegs=2, thick=0.0020)


def plant_fig(mb, rng=None, n=15, scale=1.0, pot_r=0.23, pot_h=0.33, trunk_h=0.80):
    """Fiddle-leaf fig: single trunk, branch stubs, broad ribbed oval leaves."""
    rng = rng or random.Random(17)
    plant_pot(mb, pot_r, pot_h, "concrete_raw")
    z0 = pot_h * 0.92
    trunk = [(0, 0, z0), (0.012, -0.008, z0 + trunk_h * 0.45),
             (-0.006, 0.010, z0 + trunk_h * 0.80), (0.008, 0.004, z0 + trunk_h)]
    stem(mb, trunk, r=0.017 * scale, key="wood_walnut", seg=10, taper=0.45)
    # soil bump
    lathe(mb, [(0.0, z0 - 0.012), (pot_r * 0.62, z0 - 0.014), (0.0, z0 - 0.006)],
          seg=24, key="soil")
    for i in range(n):
        t = 0.30 + 0.70 * (i / max(1, n - 1))
        a = i * 2.399 + 0.7
        bx = 0.008 * t
        bz = z0 + trunk_h * t
        out = _r(rng, 0.06, 0.20) * scale
        pet = [(bx, 0, bz),
               (bx + math.cos(a) * out * 0.45, math.sin(a) * out * 0.45, bz + 0.045 * scale),
               (bx + math.cos(a) * out, math.sin(a) * out, bz + 0.020 * scale)]
        stem(mb, pet, r=0.0060 * scale, key="plant_green_dark", seg=6, taper=0.3)
        ll = _r(rng, 0.15, 0.23) * scale
        lw = _r(rng, 0.09, 0.14) * scale
        blade(mb, pet[-1], a, ll, lw, rise=_r(rng, 0.02, 0.06),
              droop=_r(rng, 0.03, 0.09), twist=_r(rng, -0.25, 0.25),
              fold=0.26, ribs=8, rib_amp=0.0020, undulate=0.045,
              key="plant_green", segs=11, wsegs=4, thick=0.0032)


def plant_pothos(mb, rng=None, vines=9, drop=0.60, pot_r=0.15, pot_h=0.19):
    """Trailing pothos: heart leaves down a cabinet face."""
    rng = rng or random.Random(23)
    plant_pot(mb, pot_r, pot_h, "ceramic_white")
    z0 = pot_h * 0.90
    for i in range(vines):
        a = i * 2.399 + 0.3
        rr = pot_r * 0.55
        x0, y0 = math.cos(a) * rr, math.sin(a) * rr
        ln = _r(rng, 0.20, drop)
        pts = [(x0, y0, z0),
               (x0 * 1.9, y0 * 1.9, z0 - ln * 0.25),
               (x0 * 2.6, y0 * 2.6, z0 - ln * 0.62),
               (x0 * 2.7, y0 * 2.7, z0 - ln)]
        stem(mb, pts, r=0.0032, key="plant_green_dark", seg=4, taper=0.35)
        for k in range(5):
            t = 0.15 + 0.21 * k
            p = (x0 * (1 + 1.7 * t), y0 * (1 + 1.7 * t), z0 - ln * t)
            ang = a + (1.9 if k % 2 else -1.9)
            blade(mb, p, ang, _r(rng, 0.045, 0.075), _r(rng, 0.030, 0.050),
                  rise=0.004, droop=0.018, fold=0.30, ribs=3,
                  key="plant_green", segs=6, wsegs=3, thick=0.0018)


def plant_succulent(mb, rng=None, n=26, scale=1.0, pot_r=0.13, pot_h=0.15):
    """Echeveria rosette: thick spoon leaves in shrinking rings."""
    rng = rng or random.Random(29)
    plant_pot(mb, pot_r, pot_h, "ceramic_white")
    z0 = pot_h * 0.88
    for ring in range(4):
        count = max(4, n // (ring + 1) - ring * 2)
        rad = (0.16 - ring * 0.032) * scale
        for i in range(count):
            a = i * (2 * math.pi / count) + ring * 0.7
            ln = (0.085 - ring * 0.014) * scale
            n_in = 0.52 - ring * 0.10
            blade(mb, (math.cos(a) * rad * 0.5, math.sin(a) * rad * 0.5, z0 + 0.004 * ring),
                  a, ln, ln * 0.58,
                  rise=ln * (0.55 + 0.5 * ring), droop=-0.004,
                  fold=1.10, key="plant_green", segs=7, wsegs=3, thick=0.0075,
                  twist=a * 0.1)
    lathe(mb, [(0.0, z0 - 0.004), (pot_r * 0.72, z0 - 0.006), (0.0, z0 + 0.002)],
          seg=22, key="soil")


def plant_airplant(mb, rng=None, n=32, scale=1.0):
    """Tillandsia: spiky silver rosette that sits directly on a surface."""
    rng = rng or random.Random(31)
    for i in range(n):
        a = i * 2.399
        ln = _r(rng, 0.07, 0.15) * scale
        tilt = _r(rng, 0.35, 1.15)
        blade(mb, (math.cos(a) * 0.012, math.sin(a) * 0.012, 0.010),
              a, ln, ln * 0.16,
              rise=math.cos(tilt) * ln * 0.9, droop=0.02,
              fold=0.55, twist=_r(rng, -0.8, 0.8),
              key="plant_green_dark", segs=7, wsegs=2, thick=0.0022)
    lathe(mb, [(0.0, 0.0), (0.030, 0.0), (0.032, 0.008), (0.0, 0.012)],
          seg=18, key="plant_green_dark")


def plant_tree(mb, rng=None, h=2.1, scale=1.0, pot_r=0.30, pot_h=0.42, clusters=7):
    """Interior tree: tapered trunk, forked limbs, leaf clusters at the tips."""
    rng = rng or random.Random(37)
    plant_pot(mb, pot_r, pot_h, "concrete_raw")
    z0 = pot_h * 0.90
    stem(mb, [(0, 0, z0), (0.02, -0.01, z0 + h * 0.35), (-0.01, 0.015, z0 + h * 0.62),
              (0.015, 0.0, z0 + h * 0.78)],
         r=0.035 * scale, key="wood_walnut", seg=12, taper=0.55)
    top = (0.015, 0.0, z0 + h * 0.78)
    for i in range(clusters):
        a = i * 2.399 + 0.4
        reach = _r(rng, 0.22, 0.46) * scale
        rise = _r(rng, 0.10, 0.30) * scale
        mid = (top[0] + math.cos(a) * reach * 0.45, top[1] + math.sin(a) * reach * 0.45,
               top[2] + rise * 0.55)
        end = (top[0] + math.cos(a) * reach, top[1] + math.sin(a) * reach, top[2] + rise)
        stem(mb, [top, mid, end], r=0.018 * scale, key="wood_walnut", seg=9, taper=0.6)
        for k in range(9):
            aa = a + _r(rng, -1.5, 1.5)
            p = (end[0] + _r(rng, -0.05, 0.05), end[1] + _r(rng, -0.05, 0.05),
                 end[2] + _r(rng, -0.06, 0.05))
            blade(mb, p, aa, _r(rng, 0.075, 0.135) * scale,
                  _r(rng, 0.045, 0.080) * scale,
                  rise=_r(rng, -0.02, 0.05), droop=_r(rng, 0.02, 0.07),
                  fold=0.32, ribs=4, key="plant_green",
                  segs=7, wsegs=3, thick=0.0024)


# ---------------------------------------------------------------------------
# micro clutter
# ---------------------------------------------------------------------------


def book(mb, w=0.150, d=0.210, t=0.030, rotz=0.0, key="paper_dark", pages="paper"):
    """Book: two rounded cover boards, inset page block, spine bands."""
    superbox(mb, (w, d, t), (0, 0, t * 0.5), e=0.07, seg=12, rings=5, key=key,
             rot=(0, 0, rotz))
    mb.box((w - 0.008, d - 0.012, t - 0.008), (0, 0.005, t * 0.5),
           (0, 0, rotz), pages)
    for s in (-1, 1):
        mb.box((w - 0.010, 0.006, 0.005),
               (0, s * (d * 0.5 - 0.016), t * 0.5), (0, 0, rotz), key)


def books_pile(mb, n=4, rng=None):
    rng = rng or random.Random(3)
    z = 0.0
    for i in range(n):
        t = _r(rng, 0.020, 0.040)
        mb.push((0.0, 0.0, z))
        book(mb, _r(rng, 0.13, 0.20), _r(rng, 0.19, 0.26), t,
             _r(rng, -0.22, 0.22), rng.choice(["paper_dark", "fabric_navy", "brick",
                                               "paint_charcoal", "paper"]))
        mb.pop()
        z += t


def keyboard(mb, w=0.44, d=0.145, key="plastic_black"):
    """Low-profile keyboard: chassis, 5 key rows, spacebar, indicator LED."""
    superbox(mb, (w, d, 0.017), (0, 0, 0.010), e=0.14, seg=20, rings=6, key=key)
    mb.box((w - 0.02, 0.010, 0.004), (0, -d * 0.5 + 0.010, 0.019), key="metal_brushed")
    rows = 5
    for r in range(rows):
        cols = 14 - (1 if r == 0 else 0)
        for c in range(cols):
            x = -w * 0.5 + 0.030 + c * ((w - 0.055) / 13.0) + (0.007 if r == 0 else 0)
            mb.box((0.0235, 0.0215, 0.0055), (x, -d * 0.5 + 0.028 + r * 0.0235, 0.021),
                   key=key)
    mb.box((0.180, 0.0215, 0.0055), (0.0, -d * 0.5 + 0.145, 0.021), key=key)
    mb.cyl(0.0022, 0.004, (w * 0.5 - 0.030, d * 0.5 - 0.020, 0.021), seg=8,
           key="neon_grille")


def mouse(mb, key="plastic_black"):
    """Mouse: teardrop shell, scroll wheel, split buttons."""
    superbox(mb, (0.062, 0.110, 0.040), (0, 0, 0.020), e=0.62, seg=22, rings=12, key=key)
    superbox(mb, (0.050, 0.040, 0.012), (0, -0.030, 0.036), e=0.55, seg=16, rings=6, key=key)
    mb.box((0.003, 0.060, 0.008), (0, -0.012, 0.040), key="metal_black")
    mb.cyl(0.0075, 0.010, (0, 0.006, 0.036), rot=(0, math.pi / 2, 0), seg=12,
           key="rubber")


def headphones(mb, key="plastic_black"):
    """Over-ear headphones resting on a desk."""
    for sx in (-1, 1):
        lathe(mb, [(0.0, 0.0), (0.036, 0.0), (0.040, 0.012), (0.040, 0.030),
                   (0.034, 0.038), (0.0, 0.038)], loc=(sx * 0.085, 0, 0.038),
              rot=(0, math.pi / 2, 0), seg=26, key=key)
        lathe(mb, [(0.0, -0.002), (0.030, 0.000), (0.032, 0.010), (0.0, 0.012)],
              loc=(sx * 0.085, 0, 0.038), rot=(0, math.pi / 2, 0), seg=22,
              key="fabric_grey")
    band = []
    for i in range(13):
        a = math.pi * (0.10 + 0.80 * i / 12)
        band.append((math.cos(a) * 0.095, 0.0, 0.040 + math.sin(a) * 0.075))
    stem(mb, band, r=0.0085, key=key, seg=8, taper=0.1)


def phone(mb, key="plastic_black"):
    superbox(mb, (0.072, 0.150, 0.009), (0, 0, 0.0045), e=0.09, seg=16, rings=6, key=key)
    superbox(mb, (0.066, 0.140, 0.002), (0, 0, 0.0095), e=0.08, seg=14, rings=4,
             key="screen_ui")
    mb.cyl(0.004, 0.0016, (0.020, 0.050, 0.0105), seg=12, key="rubber")


def wall_socket(mb, z=0.30, key="plastic_white", gangs=2):
    """Flush wall socket: faceplate, screw, socket wells, status LED."""
    superbox(mb, (0.086, 0.012, 0.086), (0, 0.006, z), e=0.12, seg=18, rings=6, key=key)
    for g in range(gangs):
        cx = (g - (gangs - 1) / 2.0) * 0.040
        mb.cyl(0.0175, 0.014, (cx, 0.0, z), rot=(math.pi / 2, 0, 0), seg=16,
               key="paint_charcoal")
        for sx in (-1, 1):
            mb.box((0.004, 0.004, 0.012), (cx + sx * 0.006, -0.008, z), key="metal_steel")
    mb.cyl(0.0022, 0.004, (0, -0.002, z + 0.038), rot=(math.pi / 2, 0, 0), seg=8,
           key="metal_steel")


def wall_switch(mb, z=1.05, key="plastic_white", gangs=2):
    superbox(mb, (0.086, 0.010, 0.086), (0, 0.005, z), e=0.14, seg=18, rings=6, key=key)
    for g in range(gangs):
        x = (g - (gangs - 1) / 2) * 0.036
        mb.box((0.026, 0.008, 0.030), (x, -0.004, z), key=key)


def thermostat(mb, z=1.45):
    superbox(mb, (0.110, 0.020, 0.075), (0, 0.010, z), e=0.16, seg=20, rings=8,
             key="plastic_white")
    mb.box((0.070, 0.004, 0.036), (0, -0.002, z + 0.006), key="screen_ui")
    mb.cyl(0.008, 0.006, (0, -0.004, z - 0.022), rot=(math.pi / 2, 0, 0), seg=14,
           key="metal_steel")


def jar(mb, r=0.055, h=0.150, key="glass_black", cap="metal_steel"):
    """Storage jar: body, shoulder, screw collar, contents line."""
    lathe(mb, [(0.0, 0.0), (r * 0.80, 0.0), (r * 0.98, 0.010), (r, 0.030),
               (r, h * 0.80), (r * 0.92, h * 0.90), (r * 0.72, h * 0.96),
               (0.0, h * 0.96)], seg=30, key=key)
    lathe(mb, [(r * 0.74, h * 0.955), (r * 0.80, h * 1.005), (r * 0.74, h * 1.045),
               (0.0, h * 1.05)], seg=26, key=cap)
    lathe(mb, [(0.0, 0.014), (r * 0.90, 0.016), (r * 0.92, h * 0.55), (0.0, h * 0.56)],
          seg=24, key="wood_oak")


def kettle(mb, r=0.085, h=0.20):
    """Electric kettle: body, lid, spout, handle, base plate."""
    lathe(mb, [(0.0, 0.012), (r * 0.70, 0.012), (r * 0.90, 0.030), (r, 0.070),
               (r * 0.98, h * 0.70), (r * 0.92, h), (r * 0.70, h * 0.99),
               (r * 0.66, h * 0.94), (r * 0.90, h * 0.92), (0.0, h * 0.92)],
          seg=34, key="metal_steel")
    lathe(mb, [(0.0, h * 0.99), (r * 0.66, h * 0.99), (r * 0.60, h * 1.03),
               (r * 0.20, h * 1.05), (0.0, h * 1.04)], seg=24, key="plastic_black")
    lathe(mb, [(0.0, 0.0), (r * 0.92, 0.0), (r * 0.94, 0.010), (0.0, 0.012)],
          seg=28, key="plastic_black")
    stem(mb, [(r * 0.92, 0, h * 0.30), (r * 1.24, 0, h * 0.55),
              (r * 1.15, 0, h * 0.92), (r * 0.62, 0, h * 1.00)],
         r=0.011, key="plastic_black", seg=8, taper=0.15)
    stem(mb, [(r * 0.55, -0.02, h * 0.72), (r * 0.95, -0.09, h * 0.80),
              (r * 1.02, -0.10, h * 0.94)],
         r=0.016, key="metal_steel", seg=10, taper=0.35)


def cutting_board(mb, w=0.36, d=0.24, t=0.022):
    """End-grain board leaning on the backsplash."""
    superbox(mb, (w, d, t), (0, 0, d * 0.5), e=0.10, seg=20, rings=6, key="wood_oak",
             rot=(math.pi * 0.5 - 0.12, 0, 0))
    mb.cyl(0.010, t + 0.004, (w * 0.5 - 0.035, 0.0, d * 0.5), rot=(0, math.pi / 2, 0),
           seg=10, key="metal_steel")


def utensil_cup(mb, r=0.055, h=0.115):
    lathe(mb, [(0.0, 0.0), (r * 0.82, 0.0), (r * 0.86, 0.008), (r, h),
               (r * 0.94, h * 1.01), (r * 0.84, h * 0.99), (r * 0.78, h * 0.06),
               (0.0, h * 0.05)], seg=26, key="ceramic_white")
    handles = [(0.004, 0.020, 0.012), (0.010, -0.030, 0.014), (-0.012, 0.040, 0.010),
               (0.018, 0.006, 0.016), (-0.004, -0.016, 0.011)]
    for i, (dx, dy, rr) in enumerate(handles):
        a = i * 1.4
        stem(mb, [(dx * 0.4, dy * 0.4, h * 0.10),
                  (dx * 2.2, dy * 2.2, h * 0.55),
                  (dx * 3.4, dy * 3.4, h * 0.95 + rr)],
             r=rr * 0.55, key="metal_steel", seg=6, taper=0.4)
    mb.sphere(0.030, (0.0, 0.0, h * 0.88), seg=14, rings=8, key="metal_steel")


def dish_rack(mb, w=0.42, d=0.30, h=0.16):
    for sx in (-1, 1):
        mb.box((0.006, d, h), (sx * (w * 0.5 - 0.010), 0, h * 0.5), key="metal_steel")
    mb.box((w, d, 0.006), (0, 0, 0.004), key="metal_steel")
    for i in range(7):
        x = -w * 0.5 + 0.045 + i * (w - 0.09) / 6
        mb.cyl(0.0035, h * 0.92, (x, 0, h * 0.50), seg=6, key="metal_steel")
    for i in range(4):
        mb.cyl(0.090 - i * 0.004, 0.006, (-w * 0.5 + 0.10 + i * 0.085, 0.02,
                                          h * 0.30 + 0.004), seg=24,
               key="ceramic_white")
    for i in range(3):
        mb.cyl(0.036, 0.090, (0.10 + i * 0.075, -0.06, h * 0.32), seg=18,
               key="ceramic_white")


def towel(mb, w=0.50, h=0.68, drop=0.30, key="fabric_cream", bar_z=1.10):
    """Towel folded over a rail: front sheet, fold, back sheet, hem bands."""
    for dz, yy in ((0.0, -0.012), (0.0, 0.012)):
        verts = []
        cols, rows = 10, 7
        for i in range(cols + 1):
            u = i / cols
            for j in range(rows + 1):
                v = j / rows
                fold = 0.012 * math.sin(u * 9.0 + v * 3.0)
                verts.append(((u - 0.5) * w, yy + fold, bar_z + 0.02 - v * drop))
        faces = []
        for i in range(cols):
            for j in range(rows):
                a = i * (rows + 1) + j
                b = a + rows + 1
                faces.append((a, b, b + 1, a + 1))
        mb.add(verts, faces, key)
    # hem bands
    for zz in (bar_z + 0.02 - drop + 0.02, bar_z - 0.06):
        mb.box((w, 0.030, 0.014), (0, 0, zz), key="fabric_grey")


def toiletries(mb, rng=None):
    rng = rng or random.Random(41)
    specs = [(0.030, 0.115, "plastic_white"), (0.024, 0.140, "plastic_cream"),
             (0.020, 0.095, "metal_steel"), (0.026, 0.160, "glass_black"),
             (0.018, 0.120, "plastic_white")]
    for i, (r, h, key) in enumerate(specs):
        x = (i - 2) * 0.052 + _r(rng, -0.004, 0.004)
        lathe(mb, [(0.0, 0.0), (r * 0.85, 0.0), (r, 0.010), (r, h * 0.72),
                   (r * 0.72, h * 0.92), (r * 0.30, h * 0.98), (r * 0.30, h),
                   (0.0, h)], loc=(x, _r(rng, -0.02, 0.02), 0), seg=22, key=key)
        mb.cyl(r * 0.40, 0.016, (x, 0.0, h + 0.006), seg=14,
               key=rng.choice(["metal_steel", "metal_gold", "plastic_black"]))


def slippers(mb, key="fabric_grey"):
    for sx in (-1, 1):
        superbox(mb, (0.095, 0.245, 0.045), (sx * 0.075, 0, 0.023), e=0.55, seg=24,
                 rings=10, key=key)
        superbox(mb, (0.085, 0.140, 0.030), (sx * 0.075, -0.050, 0.055), e=0.60, seg=20,
                 rings=8, key="fabric_navy")


def clothes_pile(mb, rng=None, key="fabric_grey"):
    rng = rng or random.Random(43)
    for i in range(5):
        superbox(mb, (_r(rng, 0.20, 0.32), _r(rng, 0.16, 0.26), _r(rng, 0.05, 0.09)),
                 (_r(rng, -0.05, 0.05), _r(rng, -0.05, 0.05), 0.03 + i * 0.055),
                 e=0.42, seg=22, rings=10, key=key,
                 rot=(_r(rng, -0.3, 0.3), _r(rng, -0.3, 0.3), _r(rng, -0.5, 0.5)),
                 wrinkle=0.010, seed=i * 3.1)


def cable_bundle(mb, pts, n=3, r=0.0042, rng=None, key="rubber"):
    rng = rng or random.Random(47)
    for i in range(n):
        off = [(x + _r(rng, -0.006, 0.006), y + _r(rng, -0.006, 0.006), z + i * 0.001)
               for (x, y, z) in pts]
        stem(mb, off, r=r, key=key, seg=6, taper=0.0)