"""s12 -- joinery & hardware: profiled skirting, shadow gaps, door ironmongery,
window reveals, thresholds and wall panel joints.

Geometry-grade detail: every edge that catches light gets a real profile.
"""
from __future__ import annotations

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402
import furn2 as f2  # noqa: E402

CL = 2.95
OBJ = "S_joinery"

# Monospace the wall runs: (axis, fixed, a0, a1, [(gap0, gap1), ...], side)
# "side" = +1 when the room is on the +normal side of the wall face.
# For axis "x" the run is horizontal (varies in x) at y = fixed.
# normal for axis x is -y when side=-1 (room at smaller y).
RUNS = [
    # living
    ("x", 5.400, 3.960, 11.280, [(6.60, 9.60)], -1),
    ("y", 3.960, 0.160, 5.400, [], +1),
    ("y", 11.280, 0.160, 5.400, [(4.10, 5.00)], -1),
    # master
    ("x", 5.400, 0.160, 3.840, [(1.52, 2.42)], -1),
    ("y", 3.840, 0.160, 5.400, [], -1),
    ("y", 0.120, 0.160, 5.400, [], +1),
    # bed 2
    ("y", 11.400, 0.160, 5.400, [(4.10, 5.00)], +1),
    ("y", 15.880, 0.160, 5.400, [], -1),
    ("x", 5.400, 11.400, 15.840, [], -1),
    # bed 3
    ("y", 11.400, 5.520, 10.880, [(7.58, 8.48)], +1),
    ("x", 10.880, 11.400, 15.880, [], -1),
    ("x", 5.520, 11.400, 15.880, [], +1),
    # kitchen
    ("x", 6.840, 4.800, 8.640, [(5.30, 7.90)], +1),
    ("x", 10.880, 4.800, 8.640, [], -1),
    ("y", 4.800, 6.840, 10.880, [], +1),
    ("y", 8.640, 6.840, 10.880, [], -1),
    # foyer
    ("x", 6.840, 8.760, 11.280, [(9.40, 10.44)], +1),
    ("x", 10.880, 8.760, 11.280, [(9.40, 10.44)], -1),
    ("y", 8.760, 6.840, 10.880, [], +1),
    ("y", 11.280, 6.840, 10.880, [(7.58, 8.48)], -1),
    # corridor
    ("x", 6.720, 0.160, 11.280, [(1.10, 2.20), (3.48, 4.58), (5.30, 7.90), (9.40, 10.44)], -1),
    ("x", 5.520, 0.160, 11.280, [(1.52, 2.42), (4.10, 5.00), (6.60, 9.60)], +1),
    ("y", 0.120, 5.520, 6.720, [], +1),
    ("y", 11.280, 5.520, 6.720, [], -1),
    # bath 1
    ("x", 8.200, 2.840, 4.680, [(3.22, 4.18)], +1),
    ("x", 10.880, 2.840, 4.680, [], -1),
    ("y", 2.840, 8.200, 10.880, [], +1),
    ("y", 4.680, 8.200, 10.880, [], -1),
    # bath 2
    ("x", 8.200, 0.160, 2.720, [(1.14, 2.10)], +1),
    ("x", 10.880, 0.160, 2.720, [], -1),
    ("y", 0.120, 8.200, 10.880, [], +1),
    ("y", 2.720, 8.200, 10.880, [], -1),
    # utility
    ("x", 8.080, 0.160, 2.720, [(1.14, 2.10)], -1),
    ("x", 8.080, 2.840, 4.680, [(3.22, 4.18)], -1),
    ("y", 4.680, 6.840, 8.080, [], -1),
]

WOOD_ROOMS = {"master", "bed2", "bed3"}


def segments(a0, a1, gaps):
    """Split [a0, a1] at gap intervals, returning the solid spans."""
    out = []
    cur = a0
    for (g0, g1) in sorted(gaps):
        if g0 > cur:
            out.append((cur, min(g0, a1)))
        cur = max(cur, g1)
    if cur < a1:
        out.append((cur, a1))
    return [(a, b) for (a, b) in out if b - a > 0.02]


def strip(mb, axis, fixed, side, a0, a1, z, depth, height, key, inset=0.0):
    """One profiled strip along a wall face."""
    face = fixed - side * inset
    mid = (a0 + a1) * 0.5
    length = a1 - a0
    off = face + side * depth * 0.5
    if axis == "x":
        mb.box((length, depth, height), (mid, off, z + height * 0.5), key=key)
    else:
        mb.box((depth, length, height), (off, mid, z + height * 0.5), key=key)


def skirting_run(mb, axis, fixed, side, a0, a1, key):
    """Three-step skirting: plinth, bevelled body, top bead."""
    # plinth
    strip(mb, axis, fixed, side, a0, a1, 0.0, 0.026, 0.030, "paint_charcoal" if
          key.startswith("paint") else "wood_dark")
    # body
    strip(mb, axis, fixed, side, a0, a1, 0.028, 0.020, 0.052, key)
    # top bead
    strip(mb, axis, fixed, side, a0, a1, 0.078, 0.024, 0.010, key)
    # shadow line at the floor
    strip(mb, axis, fixed, side, a0, a1, 0.0, 0.008, 0.008, "grout")


def ceiling_gap(mb, axis, fixed, side, a0, a1):
    """Recessed shadow gap where wall meets ceiling."""
    strip(mb, axis, fixed, side, a0, a1, CL - 0.022, 0.014, 0.022, "grout")


def build():
    for ob in list(bpy.data.objects):
        if ob.name == OBJ or ob.name.startswith(OBJ + "."):
            bpy.data.objects.remove(ob, do_unlink=True)
    cy.col("ARCH_TRIM")
    mb = cy.MB(OBJ, "ARCH_TRIM", bevel=0.0015, bevel_seg=1)

    for i, (axis, fixed, a0, a1, gaps, side) in enumerate(RUNS):
        room = "wood" if i in () else "concrete"
        key = "wood_dark" if room == "wood" else "paint_charcoal"
        for (s0, s1) in segments(a0, a1, gaps):
            skirting_run(mb, axis, fixed, side, s0, s1, key)
            ceiling_gap(mb, axis, fixed, side, s0, s1)

    # ------------------------------------------------- wall panel joints
    # concrete board look on the living room's west + north walls
    for y in [0.55 + 1.05 * k for k in range(5)]:
        if 0.16 < y < 5.34:
            mb.box((0.004, 0.008, 2.55), (3.968, y, 1.42), key="grout")
    for x in [4.10 + 1.18 * k for k in range(6)]:
        if 4.00 < x < 11.20 and not (6.55 < x < 9.65):
            mb.box((0.008, 0.004, 2.55), (x, 5.392, 1.42), key="grout")
    mb.box((7.30, 0.006, 0.010), (7.62, 5.392, 2.50), key="grout")
    mb.box((0.006, 5.20, 0.010), (3.968, 2.78, 2.50), key="grout")

    # ------------------------------------------------------ thresholds
    for (axis, fixed, a0, a1) in [
        ("x", 5.460, 1.52, 2.42), ("y", 11.340, 4.10, 5.00),
        ("x", 8.140, 1.14, 2.10), ("x", 8.140, 3.22, 4.18),
        ("y", 11.340, 7.58, 8.48), ("x", 6.780, 5.30, 7.90),
        ("x", 5.460, 6.60, 9.60), ("x", 10.940, 9.40, 10.44),
    ]:
        if axis == "x":
            mb.box((a1 - a0, 0.15, 0.012), ((a0 + a1) / 2, fixed, 0.008), key="metal_steel")
        else:
            mb.box((0.15, a1 - a0, 0.012), (fixed, (a0 + a1) / 2, 0.008), key="metal_steel")

    # Moving hardware belongs to the independent runtime door meshes.

    # ------------------------------------------------- window reveals
    # living glazing: floor track + head reveal + mullion caps
    mb.box((7.34, 0.16, 0.022), (7.62, -0.020, 0.012), key="metal_steel")
    mb.box((7.34, 0.18, 0.032), (7.62, -0.020, 2.462), key="metal_dark")
    for x in (4.02, 5.82, 7.62, 9.42, 11.22):
        mb.box((0.105, 0.20, 0.045), (x, -0.020, 2.435), key="metal_dark")
        mb.box((0.105, 0.20, 0.045), (x, -0.020, 0.185), key="metal_dark")
    # slider hardware
    mb.box((0.035, 0.075, 0.30), (9.16, -0.075, 1.05), key="metal_brushed")
    mb.cyl(0.010, 0.09, (9.16, -0.105, 1.05), rot=(0, math.pi / 2, 0), seg=10,
           key="metal_brushed")
    # bedroom windows: latches and gaskets
    for (x0, x1, z) in [(0.62, 3.36, 2.70), (11.98, 15.56, 2.70)]:
        for x in (x0 + 0.30, (x0 + x1) * 0.5, x1 - 0.30):
            mb.push((x, 0.035, z - 0.20), 0)
            mb.box((0.055, 0.045, 0.028), (0, 0, 0), key="metal_brushed")
            mb.box((0.085, 0.020, 0.012), (0, -0.020, -0.014), key="metal_brushed")
            mb.pop()
        mb.box((x1 - x0 - 0.04, 0.012, 0.014), ((x0 + x1) / 2, 0.030, z + 0.03),
               key="rubber")
    # east window latch
    mb.push((15.90, 8.20, 1.35), -math.pi / 2)
    mb.box((0.050, 0.042, 0.026), (0, 0, 0), key="metal_brushed")
    mb.pop()

    # -------------------------------------------- cable trunking, corridor
    for x0, x1 in [(0.30, 3.20), (4.00, 5.10), (7.95, 11.15)]:
        mb.box((x1 - x0, 0.055, 0.038), ((x0 + x1) / 2, 6.692, CL - 0.055),
               key="plastic_white")
        for x in (x0 + 0.06, x1 - 0.06):
            mb.box((0.070, 0.060, 0.050), (x, 6.692, CL - 0.055), key="plastic_white")
    # down-drop to the wall sockets
    mb.box((0.045, 0.040, 1.24), (3.988, 1.12, 1.55), key="plastic_white")
    mb.box((0.045, 0.040, 1.24), (3.988, 0.86, 1.55), key="plastic_white")

    mb.build()

    # ------------------------------------------------------------- stats
    ob = bpy.data.objects[OBJ]
    ob.data.calc_loop_triangles()
    return {"object": OBJ, "verts": len(ob.data.vertices),
            "tris": len(ob.data.loop_triangles)}


_result = build()
print(_result, flush=True)