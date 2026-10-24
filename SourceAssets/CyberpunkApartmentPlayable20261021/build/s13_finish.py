"""s13 -- surface finish pass: tiled wainscots, tile joints, LED skirting glow,
shower niches and wall hooks.  Cheap geometry, strong read at render size.
"""
from __future__ import annotations

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402

OBJ = "S_finish"


def segments(a0, a1, gaps):
    out, cur = [], a0
    for (g0, g1) in sorted(gaps):
        if g0 > cur:
            out.append((cur, min(g0, a1)))
        cur = max(cur, g1)
    if cur < a1:
        out.append((cur, a1))
    return [(a, b) for (a, b) in out if b - a > 0.02]


def panel(mb, axis, fixed, side, a0, a1, z0, z1, thick, key):
    mid, ln = (a0 + a1) * 0.5, a1 - a0
    off = fixed + side * thick * 0.5
    if axis == "x":
        mb.box((ln, thick, z1 - z0), (mid, off, (z0 + z1) * 0.5), key=key)
    else:
        mb.box((thick, ln, z1 - z0), (off, mid, (z0 + z1) * 0.5), key=key)


def build():
    for ob in list(bpy.data.objects):
        if ob.name == OBJ or ob.name.startswith(OBJ + "."):
            bpy.data.objects.remove(ob, do_unlink=True)
    cy.col("ARCH_TRIM")
    mb = cy.MB(OBJ, "ARCH_TRIM", bevel=0.001, bevel_seg=1)

    # ------------------------------------------------ tiled wainscots
    WAINSCOT = [
        # bath 1
        ("x", 8.200, +1, 2.840, 4.680, [(3.22, 4.18)]),
        ("x", 10.880, -1, 2.840, 4.680, []),
        ("y", 2.840, +1, 8.200, 10.880, []),
        ("y", 4.680, -1, 8.200, 10.880, []),
        # bath 2
        ("x", 8.200, +1, 0.120, 2.720, [(1.14, 2.10)]),
        ("x", 10.880, -1, 0.120, 2.720, []),
        ("y", 0.120, +1, 8.200, 10.880, []),
        ("y", 2.720, -1, 8.200, 10.880, []),
        # utility room
        ("x", 8.080, +1, 0.120, 2.720, [(1.14, 2.10)]),
        ("x", 8.080, +1, 2.840, 4.680, [(3.22, 4.18)]),
        ("y", 4.680, -1, 6.840, 8.080, []),
        # kitchen backsplash side walls
        ("y", 4.800, +1, 6.840, 10.880, []),
        ("y", 8.640, -1, 6.840, 10.880, []),
    ]
    Z0, Z1 = 0.083, 1.34
    for (axis, fixed, side, a0, a1, gaps) in WAINSCOT:
        for (s0, s1) in segments(a0, a1, gaps):
            panel(mb, axis, fixed, side, s0, s1, Z0, Z1, 0.012, "tile_bath")
            # chrome cap rail over the tile
            panel(mb, axis, fixed, side, s0, s1, Z1, Z1 + 0.014, 0.018, "metal_brushed")
            # silicon joint at the top of the skirting
            panel(mb, axis, fixed, side, s0, s1, Z0 - 0.004, Z0 + 0.002, 0.016, "grout")

    # tile field joints: 0.30 m module, thin grout lines proud of the face
    for (axis, fixed, side, a0, a1, gaps) in WAINSCOT:
        n = int((a1 - a0) / 0.30)
        for k in range(1, n):
            p = a0 + k * 0.30
            if any(g0 - 0.02 < p < g1 + 0.02 for (g0, g1) in gaps):
                continue
            if axis == "x":
                mb.box((0.006, 0.014, Z1 - Z0), (p, fixed + side * 0.012, (Z0 + Z1) * 0.5),
                       key="grout")
            else:
                mb.box((0.014, 0.006, Z1 - Z0), (fixed + side * 0.012, p, (Z0 + Z1) * 0.5),
                       key="grout")
        for z in (Z0 + 0.30, Z0 + 0.60, Z0 + 0.90):
            for s0, s1 in segments(a0, a1, gaps):
                panel(mb, axis, fixed, side, s0, s1, z, z + 0.004, 0.014, "grout")

    # ------------------------------------------------- floor tile joints
    TILE_ROOMS = [(0.12, 8.20, 2.72, 10.88), (2.84, 8.20, 4.68, 10.88),
                  (2.84, 6.84, 4.68, 8.08), (4.80, 6.84, 8.64, 10.88),
                  (8.76, 6.84, 11.28, 10.88), (0.12, 6.72, 2.72, 8.08)]
    for (x0, y0, x1, y1) in TILE_ROOMS:
        x = x0 + 0.60
        while x < x1 - 0.05:
            mb.box((0.006, y1 - y0, 0.003), (x, (y0 + y1) * 0.5, 0.0026), key="grout")
            x += 0.60
        y = y0 + 0.60
        while y < y1 - 0.05:
            mb.box((x1 - x0, 0.006, 0.003), ((x0 + x1) * 0.5, y, 0.0026), key="grout")
            y += 0.60

    # concrete expansion joints, living + corridor
    for x in (5.40, 7.40, 9.40):
        mb.box((0.008, 5.20, 0.004), (x, 2.76, 0.0028), key="grout")
    mb.box((7.28, 0.008, 0.004), (7.62, 2.76, 0.0028), key="grout")
    for y in (6.00, 6.40):
        mb.box((11.10, 0.008, 0.004), (5.70, y, 0.0028), key="grout")

    # --------------------------------------------------- LED skirting glow
    GLOW = [
        ("x", 5.386, 3.99, 11.26, [(6.62, 9.58)]),
        ("y", 3.964, 0.20, 5.36, []),
        ("y", 11.276, 0.20, 5.36, [(4.10, 5.00)]),
        ("x", 6.712, 0.20, 11.26, [(1.10, 2.20), (3.48, 4.58), (5.30, 7.90), (9.40, 10.44)]),
        ("x", 5.526, 3.99, 6.56, []),
        ("x", 5.526, 9.64, 11.26, []),
    ]
    for (axis, fixed, a0, a1, gaps) in GLOW:
        for (s0, s1) in segments(a0, a1, gaps):
            for z, key in ((0.014, "neon_strip_cool"),):
                if axis == "x":
                    mb.box((s1 - s0, 0.010, 0.010), ((s0 + s1) * 0.5, fixed, z), key=key)
                else:
                    mb.box((0.010, s1 - s0, 0.010), (fixed, (s0 + s1) * 0.5, z), key=key)

    # ---------------------------------------------------- shower details
    # niche in the bath-1 shower wall
    mb.box((0.46, 0.02, 0.34), (3.86, 10.868, 1.30), key="tile_bath")
    mb.box((0.42, 0.05, 0.012), (3.86, 10.878, 1.142), key="metal_brushed")
    mb.box((0.42, 0.05, 0.012), (3.86, 10.878, 1.462), key="metal_brushed")
    for (dx, h, r) in ((-0.12, 0.16, 0.030), (0.02, 0.20, 0.034), (0.13, 0.13, 0.026)):
        mb.cyl(r, h, (3.86 + dx, 10.862, 1.148 + h * 0.5), seg=18, key="plastic_white")
        mb.cyl(r * 0.45, 0.020, (3.86 + dx, 10.862, 1.148 + h + 0.010), seg=12,
               key="metal_steel")
    # linear drain + glass clamps
    mb.box((0.60, 0.055, 0.008), (3.86, 9.80, 0.006), key="metal_steel")
    for y in (9.66, 10.90):
        mb.box((0.04, 0.04, 0.05), (3.30, y, 1.10), key="metal_brushed")

    # ------------------------------------------------------- wall hooks
    for (x, y, rz, z) in [(2.90, 9.62, math.pi / 2, 1.62), (3.86, 8.30, 0.0, 1.55),
                          (0.18, 9.60, math.pi / 2, 1.55)]:
        mb.push((x, y, z), rz)
        mb.box((0.030, 0.012, 0.075), (0, 0, 0), key="metal_brushed")
        mb.cyl(0.008, 0.055, (0, -0.026, 0.010), rot=(math.pi / 2, 0, 0), seg=10,
               key="metal_brushed")
        mb.sphere(0.010, (0, -0.052, 0.010), seg=10, rings=6, key="metal_brushed")
        mb.pop()

    mb.build()
    ob = bpy.data.objects[OBJ]
    ob.data.calc_loop_triangles()
    return {"object": OBJ, "verts": len(ob.data.vertices),
            "tris": len(ob.data.loop_triangles)}


_result = build()
print(_result, flush=True)