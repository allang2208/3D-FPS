"""s1 — architecture shell.

16.0 x 11.0 m floor plate, 2.95 m ceilings.
         Y=11 (back wall, entry door at X 9.4..10.4)
  +------------------------------------------------------+
  | BATH2    | BATH1 |  KITCHEN     |  FOYER  | BED3     |
  | 0-2.72   |2.84-  | 4.98-8.64    |8.76-11.28|11.4-15.88|
  | 8.2-11   |4.68   | 6.84-11      |6.84-11   |5.52-10.88|
  +----+-----+-------+--------------+---------+          |
  | ALCOVE   |       |                                     |
  | 2.84-4.68            CORRIDOR  Y 5.52..6.72  X 0..11.28|
  +----------------------------------------------+-------+
  | MASTER (wood)    |  LIVING  (concrete)       | BED2  |
  | 0-3.84           |  3.96-11.28               |11.4-  |
  | Y 0-5.4          |  Y 0-5.4                  |15.88  |
  +------------------+---------------------------+-------+
         Y=0 facade, full-height glazing, balcony in front
"""
from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402

CL = 2.95          # ceiling height
T_EXT = 0.24       # exterior wall thickness
T_INT = 0.12       # interior partition thickness


def door_leaf(mb, hinge, width, height, thick, angle, key, axis="x", swing=1):
    """A door leaf as a box rotated about a vertical hinge."""
    hx, hy = hinge
    a = math.radians(angle) * swing
    if axis == "x":
        dirv = Vector((math.cos(a), math.sin(a), 0))
    else:
        dirv = Vector((math.sin(a), math.cos(a), 0))
    cx = hx + dirv.x * width / 2
    cy = hy + dirv.y * width / 2
    rot = math.atan2(dirv.y, dirv.x)
    mb.box((width, thick, height), (cx, cy, height / 2), (0, 0, rot), key=key)


def build() -> dict:
    for c in ("ARCH_SLABS", "ARCH_WALLS", "ARCH_FACADE", "ARCH_BALCONY",
              "ARCH_CEILING", "ARCH_FLOORS", "ARCH_TRIM", "ARCH_DOORS"):
        cy.reset_col(c)

    # ---------------------------------------------------------------- slabs
    mb = cy.MB("S_plate", "ARCH_SLABS", bevel=0.005)
    mb.box((16.6, 11.6, 0.34), (8.0, 5.5, -0.17), key="concrete_raw")
    mb.box((16.6, 11.6, 0.32), (8.0, 5.5, 3.11), key="concrete_ceiling")
    # balcony slab + soffit
    mb.box((7.44, 2.94, 0.18), (7.60, -1.42, -0.16), key="concrete_raw")
    mb.box((7.44, 2.94, 0.30), (7.60, -1.42, 3.13), key="concrete_ceiling")
    mb.build()

    # ------------------------------------------------------------ floors
    mb = cy.MB("S_floors", "ARCH_FLOORS")
    F = 0.002
    rooms = [
        ("concrete_floor", 3.96, 0.12, 11.28, 5.40),
        ("wood_floor", 0.12, 0.12, 3.84, 5.40),
        ("wood_floor", 11.40, 0.12, 15.88, 5.40),
        ("wood_floor", 11.40, 5.52, 15.88, 10.88),
        ("concrete_floor", 0.12, 5.52, 11.28, 6.72),
        ("concrete_floor", 0.12, 6.72, 2.72, 8.08),
        ("tile_bath", 0.12, 8.20, 2.72, 10.88),
        ("tile_bath", 2.84, 8.20, 4.68, 10.88),
        ("tile_bath", 2.84, 6.84, 4.68, 8.08),
        ("tile_bath", 4.80, 6.84, 8.64, 10.88),
        ("marble", 8.76, 6.84, 11.28, 10.88),
    ]
    for key, x0, y0, x1, y1 in rooms:
        mb.quad((x0, y0, F), (x1, y0, F), (x1, y1, F), (x0, y1, F), key)
    # balcony deck
    mb.quad((3.98, -2.80, -0.030), (3.98, -0.02, -0.030),
            (11.30, -0.02, -0.030), (11.30, -2.80, -0.030), "deck_wet")
    mb.build()

    # --------------------------------------------------------------- walls
    mb = cy.MB("S_walls", "ARCH_WALLS", bevel=0.004, bevel_seg=1)
    W = T_INT / 2
    # exterior shell
    cy.wall_run(mb, "y", 0.0, 11.0, 0.0, 0.0, CL, T_EXT, "concrete_wall")
    cy.wall_run(mb, "y", 0.0, 11.0, 16.0, 0.0, CL, T_EXT, "concrete_wall",
                openings=[(6.80, 9.60, 0.42, 2.62)])
    cy.wall_run(mb, "x", 0.0, 16.0, 11.0, 0.0, CL, T_EXT, "concrete_wall",
                openings=[(9.40, 10.44, 0.0, 2.18)])
    # facade: only the spandrel band below/above glazing + piers between rooms
    cy.wall_run(mb, "x", 0.0, 16.0, 0.0, 0.0, 0.16, T_EXT, "concrete_wall", openings=[(7.00, 8.10, 0.0, 0.16)])
    cy.wall_run(mb, "x", 0.0, 16.0, 0.0, 2.74, CL, T_EXT, "concrete_wall")
    for (a0, a1) in [(0.0, 0.62), (3.36, 4.02), (11.24, 11.98), (15.56, 16.0)]:
        cy.wall_run(mb, "x", a0, a1, 0.0, 0.16, 2.74, T_EXT, "concrete_wall")

    # interior partitions
    cy.wall_run(mb, "y", 0.0, 5.40, 3.90, 0.0, CL, T_INT, "plaster")
    # East partition is emitted once below, with both bedroom doorways.
    cy.wall_run(mb, "x", 0.0, 11.34, 5.46, 0.0, CL, T_INT, "plaster",
                openings=[(1.52, 2.42, 0.0, 2.08), (6.60, 9.60, 0.0, 2.42)])
    cy.wall_run(mb, "x", 11.34, 16.0, 5.46, 0.0, CL, T_INT, "plaster")
    cy.wall_run(mb, "y", 0.0, 11.0, 11.34, 0.0, CL, T_INT, "plaster",
                openings=[(4.10, 5.00, 0.0, 2.08), (7.58, 8.48, 0.0, 2.08)])
    cy.wall_run(mb, "x", 0.0, 11.34, 6.78, 0.0, CL, T_INT, "plaster",
                openings=[(1.10, 2.20, 0.0, 2.42), (3.48, 4.58, 0.0, 2.42), (5.30, 7.90, 0.0, 2.42), (9.40, 10.44, 0.0, 2.42)])
    cy.wall_run(mb, "x", 0.0, 2.72, 8.14, 0.0, CL, T_INT, "plaster",
                openings=[(1.14, 2.10, 0.0, 2.06)])
    cy.wall_run(mb, "x", 2.84, 4.68, 8.14, 0.0, CL, T_INT, "plaster",
                openings=[(3.22, 4.18, 0.0, 2.06)])
    cy.wall_run(mb, "y", 6.78, 11.0, 2.78, 0.0, CL, T_INT, "plaster")
    cy.wall_run(mb, "y", 6.78, 11.0, 4.74, 0.0, CL, T_INT, "plaster")
    cy.wall_run(mb, "y", 6.84, 11.0, 8.70, 0.0, CL, T_INT, "plaster")
    mb.build()

    # ------------------------------------------------------------- facade
    mb = cy.MB("S_facade", "ARCH_FACADE", bevel=0.003, bevel_seg=1)
    # structural mullions across the living glazing
    mull = [4.02, 5.82, 7.00, 8.10, 9.42, 11.22]  # clear balcony opening
    for x in mull:
        mb.box((0.085, 0.16, 2.58), (x, -0.02, 1.45), key="metal_dark")
    # transom at 2.45
    mb.box((7.3, 0.10, 0.055), (7.62, -0.02, 2.45), key="metal_dark")
    # master + bed2 windows: frames
    for (x0, x1) in [(0.62, 3.36), (11.98, 15.56)]:
        mb.box((x1 - x0, 0.13, 0.055), ((x0 + x1) / 2, -0.02, 2.70), key="metal_dark")
        mb.box((x1 - x0, 0.13, 0.09), ((x0 + x1) / 2, -0.02, 0.20), key="metal_dark")
        for x in (x0, (x0 + x1) / 2, x1):
            mb.box((0.07, 0.13, 2.5), (x, -0.02, 1.42), key="metal_dark")
    # east window (bed3) frames on X=16
    mb.box((0.12, 2.86, 0.06), (15.98, 8.20, 2.60), key="metal_dark")
    mb.box((0.12, 2.86, 0.09), (15.98, 8.20, 0.44), key="metal_dark")
    for y in (6.80, 8.20, 9.60):
        mb.box((0.12, 0.07, 2.16), (15.98, y, 1.52), key="metal_dark")
    # sliding door track + rollers
    mb.box((2.55, 0.11, 0.09), (8.10, -0.02, 2.40), key="metal_steel")
    mb.box((2.55, 0.06, 0.03), (8.10, -0.09, 0.05), key="metal_steel")
    mb.build()

    mbg = cy.MB("S_glazing", "ARCH_FACADE")
    # living glass wall (fixed panes + sliding door)
    mbg.quad((4.02, -0.055, 0.16), (4.02, -0.055, 2.44), (7.00, -0.055, 2.44), (7.00, -0.055, 0.16), "glass_window")
    mbg.quad((8.10, -0.055, 0.16), (8.10, -0.055, 2.44), (11.22, -0.055, 2.44), (11.22, -0.055, 0.16), "glass_window")
    # Balcony moving glass is authored as an independent door asset.
    # bedroom windows
    mbg.quad((0.66, -0.055, 0.24), (0.66, -0.055, 2.67), (3.32, -0.055, 2.67), (3.32, -0.055, 0.24), "glass_window")
    mbg.quad((12.02, -0.055, 0.24), (12.02, -0.055, 2.67), (15.52, -0.055, 2.67), (15.52, -0.055, 0.24), "glass_window")
    # east window
    mbg.quad((15.965, 6.84, 0.47), (15.965, 9.56, 0.47), (15.965, 9.56, 2.58), (15.965, 6.84, 2.58), "glass_window")
    mbg.build()

    # ------------------------------------------------------------ balcony
    mb = cy.MB("S_balcony", "ARCH_BALCONY", bevel=0.004, bevel_seg=1)
    # side privacy fins
    for x in (3.98, 11.30):
        mb.box((0.16, 2.86, 2.20), (x, -1.42, 1.07), key="concrete_wall")
    # glass railing posts + top rail
    for i in range(6):
        x = 4.10 + i * (7.08 / 5)
        mb.box((0.06, 0.06, 1.06), (x, -2.78, 0.52), key="metal_steel")
    mb.box((7.30, 0.09, 0.07), (7.64, -2.78, 1.09), key="metal_steel")
    mb.box((7.30, 0.05, 0.02), (7.64, -2.78, 0.03), key="metal_steel")
    # railing support brackets to the slab edge
    for i in range(6):
        x = 4.10 + i * (7.08 / 5)
        mb.box((0.05, 0.22, 0.05), (x, -2.66, -0.02), key="metal_steel")
    # drainage channel
    mb.box((7.30, 0.10, 0.05), (7.64, -2.66, -0.045), key="metal_dark")
    # soffit downlights housing
    for i in range(5):
        x = 4.4 + i * 1.6
        mb.cyl(0.055, 0.05, (x, -2.4, 2.97), seg=12, key="metal_dark")
    mb.build()

    mbg = cy.MB("S_balcony_glass", "ARCH_BALCONY")
    mbg.quad((4.06, -2.79, 0.04), (4.06, -2.79, 1.06), (11.22, -2.79, 1.06), (11.22, -2.79, 0.04), "glass_balcony")
    mbg.build()

    # ------------------------------------------------------------- ceiling
    mb = cy.MB("S_ceiling", "ARCH_CEILING", bevel=0.004, bevel_seg=1)
    # exposed structural beams
    for (x0, y0, x1, y1, h) in [
        (3.90, 0.0, 3.90, 5.46, 0.24), (11.34, 0.0, 11.34, 5.46, 0.24),
        (0.0, 5.46, 16.0, 5.46, 0.22), (0.0, 6.78, 11.34, 6.78, 0.20),
    ]:
        if abs(x1 - x0) < 0.001:
            mb.box((0.30, y1 - y0, h), (x0, (y0 + y1) / 2, CL - h / 2), key="concrete_ceiling")
        else:
            mb.box((x1 - x0, 0.30, h), ((x0 + x1) / 2, y0, CL - h / 2), key="concrete_ceiling")
    # living room drop beam
    mb.box((7.3, 0.26, 0.20), (7.62, 2.30, CL - 0.10), key="concrete_ceiling")
    # recessed tray in the living room
    for (a, b, c, d) in [(4.26, 0.42, 11.0, 0.55), (4.26, 4.05, 11.0, 4.18),
                         (4.26, 0.42, 4.39, 4.18), (10.87, 0.42, 11.0, 4.18)]:
        mb.box((c - a, d - b, 0.06), ((a + c) / 2, (b + d) / 2, CL - 0.03), key="concrete_ceiling")
    # kitchen bulkhead
    mb.box((3.90, 1.30, 0.22), (6.72, 9.90, CL - 0.11), key="plaster")
    mb.build()

    # --------------------------------------------------------------- trim
    mb = cy.MB("S_trim", "ARCH_TRIM", bevel=0.002, bevel_seg=1)
    # skirting is built by s12_joinery.py (profiled, with door gaps)
    # window sills
    mb.box((2.66, 0.26, 0.05), (1.99, 0.14, 0.235), key="marble")
    mb.box((3.50, 0.26, 0.05), (13.77, 0.14, 0.235), key="marble")
    mb.box((0.26, 2.72, 0.05), (15.85, 8.20, 0.435), key="marble")
    mb.build()

    # -------------------------------------------------------------- doors
    mb = cy.MB("S_doors", "ARCH_DOORS", bevel=0.003, bevel_seg=1)
    # frames
    def frame(axis, a0, a1, fixed, z_top):
        if axis == "x":
            mb.box((0.07, 0.14, z_top), (a0, fixed, z_top / 2), key="metal_dark")
            mb.box((0.07, 0.14, z_top), (a1, fixed, z_top / 2), key="metal_dark")
            mb.box((a1 - a0, 0.14, 0.07), ((a0 + a1) / 2, fixed, z_top + 0.035), key="metal_dark")
        else:
            mb.box((0.14, 0.07, z_top), (fixed, a0, z_top / 2), key="metal_dark")
            mb.box((0.14, 0.07, z_top), (fixed, a1, z_top / 2), key="metal_dark")
            mb.box((0.14, a1 - a0, 0.07), (fixed, (a0 + a1) / 2, z_top + 0.035), key="metal_dark")

    frame("x", 1.52, 2.42, 5.46, 2.08)          # master
    frame("y", 4.10, 5.00, 11.34, 2.08)         # bed2
    frame("x", 1.14, 2.10, 8.14, 2.06)          # bath2
    frame("x", 3.22, 4.18, 8.14, 2.06)          # bath1
    frame("y", 7.58, 8.48, 11.34, 2.08)         # bed3
    frame("x", 5.30, 7.90, 6.78, 2.42)          # kitchen cased opening
    frame("x", 6.60, 9.60, 5.46, 2.42)          # living cased opening
    frame("x", 9.40, 10.44, 11.0, 2.18)         # entry
    # All leaves are runtime ColdSteelSlidingDoor components.
    mb.build()

    # ------------------------------------------------------------- stats
    objs = []
    for c in ("ARCH_SLABS", "ARCH_WALLS", "ARCH_FACADE", "ARCH_BALCONY",
              "ARCH_CEILING", "ARCH_FLOORS", "ARCH_TRIM", "ARCH_DOORS"):
        cc = bpy.data.collections.get(c)
        if cc:
            objs.extend(cc.objects)
    tris = sum(len(o.data.loop_triangles) for o in objs if o.type == "MESH"
               for _ in [o.data.calc_loop_triangles()])
    return {"objects": len(objs), "tris": tris,
            "names": sorted(o.name for o in objs)}


_result = build()
print(_result, flush=True)