"""s11 -- micro-detail pass: extra plants, desk clutter, wall hardware.

Runs after s0..s6 (it adds to the existing collections instead of resetting
them, so re-running a room stage means re-running this one afterwards).
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
import furn2 as f2  # noqa: E402

R = random.Random

MICRO = ["LIV_micro", "LIV_micro_clutter", "KIT_micro", "KIT_micro_table", "MST_micro",
         "B2_micro", "B3_micro", "BA1_micro", "BA2_micro", "FOY_micro", "COR_micro",
         "BAL_micro"]


def build():
    for name in MICRO:
        for ob in list(bpy.data.objects):
            if ob.name == name or ob.name.startswith(name + "."):
                bpy.data.objects.remove(ob, do_unlink=True)
    made = []

    def mb_new(name, col, bevel=0.0):
        cy.col(col)
        mb = cy.MB(name, col, bevel=bevel)
        made.append(name)
        return mb

    # ------------------------------------------------------------- living
    mb = mb_new("LIV_micro", "LIVING")
    # console-top planting (the media bench sits at x 9.75..11.35, y 0.34..0.76)
    mb.push((10.18, 0.55, 0.38))
    f2.plant_pothos(mb, R(61), vines=10, drop=0.62)
    mb.pop()
    mb.push((11.06, 0.52, 0.38))
    f2.plant_airplant(mb, R(62), n=30, scale=1.15)
    mb.pop()
    # succulent on the side table
    mb.push((10.95, 1.05, 0.52))
    f2.plant_succulent(mb, R(63), scale=0.72)
    mb.pop()
    # small fern on a bookshelf
    mb.push((5.48, 5.22, 1.478))
    f2.plant_fern(mb, R(64), fronds=8, scale=0.42, pot_r=0.115, pot_h=0.15)
    mb.pop()
    # interior tree at the north edge of the rug
    mb.push((7.10, 4.72, 0.014))
    f2.plant_tree(mb, R(65), h=2.05, scale=0.92)
    mb.pop()
    # wall hardware: sockets behind the media wall, switch by the opening
    mb.push((3.985, 1.12, 0.30), math.pi / 2)
    f2.wall_socket(mb, z=0.0, gangs=2)
    mb.pop()
    mb.push((3.985, 0.86, 0.30), math.pi / 2)
    f2.wall_socket(mb, z=0.0, gangs=1)
    mb.pop()
    mb.push((4.34, 5.385, 1.05), 0.0)
    f2.wall_switch(mb, z=0.0, gangs=2)
    mb.pop()
    mb.push((4.68, 5.385, 1.28), 0.0)
    f2.thermostat(mb, z=0.0)
    mb.pop()
    # cable drop from the panel to the floor
    mb.push((0, 0, 0))
    f2.cable_bundle(mb, [(4.40, 2.60, 0.42), (4.43, 2.63, 0.16), (4.52, 2.72, 0.012),
                         (4.70, 2.86, 0.010)], n=2)
    mb.pop()
    mb.build()

    mb = mb_new("LIV_micro_clutter", "LIVING")
    # coffee table: keyboard, mouse, phone
    mb.push((8.24, 2.62, 0.362), -0.06)
    f2.keyboard(mb)
    mb.pop()
    mb.push((8.68, 2.66, 0.362), -0.06)
    f2.mouse(mb)
    mb.pop()
    mb.push((7.74, 2.72, 0.362), 0.42)
    f2.phone(mb)
    mb.pop()
    mb.push((7.48, 2.98, 0.362))
    f2.books_pile(mb, 3, R(66))
    mb.pop()
    # slippers and a pile of clothes on the floor
    mb.push((9.24, 4.16, 0.014), 0.55)
    f2.slippers(mb)
    mb.pop()
    mb.push((6.32, 4.02, 0.014), 0.9)
    f2.clothes_pile(mb, R(67))
    mb.pop()
    mb.build()

    # ------------------------------------------------------------ kitchen
    mb = mb_new("KIT_micro", "KITCHEN")
    mb.push((4.98, 10.44, 0.922))
    f2.utensil_cup(mb)
    mb.pop()
    mb.push((5.44, 10.60, 0.922))
    f2.dish_rack(mb)
    mb.pop()
    mb.push((7.12, 10.70, 0.922))
    f2.jar(mb, 0.058, 0.155)
    mb.pop()
    mb.push((7.36, 10.70, 0.922))
    f2.jar(mb, 0.052, 0.135, cap="metal_gold")
    mb.pop()
    mb.push((7.62, 10.76, 0.922), -0.15)
    f2.cutting_board(mb)
    mb.pop()
    mb.push((7.92, 10.62, 0.922))
    f2.plant_succulent(mb, R(68), scale=0.55, pot_r=0.105, pot_h=0.12)
    mb.pop()
    mb.push((5.06, 10.236, 1.04), 0.0)
    f2.wall_socket(mb, z=0.0, gangs=2)
    mb.pop()
    mb.build()

    mb = mb_new("KIT_micro_table", "KITCHEN")
    mb.push((6.70, 8.15, 0.752))
    f2.plant_airplant(mb, R(69), n=26, scale=1.35)
    mb.pop()
    mb.push((6.24, 7.98, 0.752))
    furn.mug(mb, key="ceramic_white")
    mb.pop()
    mb.push((7.16, 8.32, 0.752))
    furn.mug(mb, key="plastic_cream")
    mb.pop()
    mb.push((6.92, 8.44, 0.752))
    furn.bowl(mb, 0.105, 0.062, "metal_steel")
    mb.pop()
    mb.build()

    # ------------------------------------------------------------- master
    mb = mb_new("MST_micro", "MASTER")
    mb.push((0.58, 1.30, 0.582), 0.5)
    f2.phone(mb)
    mb.pop()
    mb.push((0.26, 3.84, 0.582), -0.3)
    f2.books_pile(mb, 2, R(70))
    mb.pop()
    mb.push((1.05, 4.95, 0.842), 0.2)
    f2.clothes_pile(mb, R(71))
    mb.pop()
    mb.push((1.62, 4.42, 0.014), 1.1)
    f2.slippers(mb)
    mb.pop()
    mb.push((0.185, 4.30, 1.05), math.pi / 2)
    f2.wall_switch(mb, z=0.0, gangs=1)
    mb.pop()
    mb.push((3.42, 0.62, 0.014))
    f2.plant_fig(mb, R(72), n=15, scale=0.86, pot_r=0.21, pot_h=0.31)
    mb.pop()
    mb.build()

    # -------------------------------------------------------------- bed 2
    mb = mb_new("B2_micro", "BED2")
    mb.push((13.26, 0.70, 0.742))
    f2.keyboard(mb)
    mb.pop()
    mb.push((13.68, 0.74, 0.742))
    f2.mouse(mb)
    mb.pop()
    mb.push((12.62, 0.58, 0.742), 0.3)
    f2.headphones(mb)
    mb.pop()
    mb.push((15.42, 4.30, 0.512), 0.4)
    f2.phone(mb)
    mb.pop()
    mb.push((14.20, 1.42, 0.014), 1.9)
    f2.slippers(mb)
    mb.pop()
    mb.push((13.90, 4.30, 0.014), 0.7)
    f2.clothes_pile(mb, R(73))
    mb.pop()
    mb.push((11.425, 1.20, 0.30), math.pi / 2)
    f2.wall_socket(mb, z=0.0, gangs=2)
    mb.pop()
    mb.build()

    # -------------------------------------------------------------- bed 3
    mb = mb_new("B3_micro", "BED3")
    mb.push((15.08, 8.20, 0.742), math.pi / 2)
    f2.keyboard(mb)
    mb.pop()
    mb.push((15.02, 8.62, 0.742), math.pi / 2)
    f2.mouse(mb)
    mb.pop()
    mb.push((15.05, 7.62, 0.742), math.pi / 2 + 0.4)
    f2.headphones(mb)
    mb.pop()
    mb.push((11.56, 8.90, 1.042), -math.pi / 2)
    f2.plant_pothos(mb, R(74), vines=8, drop=0.58, pot_r=0.13, pot_h=0.17)
    mb.pop()
    mb.push((14.30, 6.95, 0.014), 0.4)
    f2.clothes_pile(mb, R(75))
    mb.pop()
    mb.push((12.62, 9.90, 0.014), 1.3)
    f2.slippers(mb)
    mb.pop()
    mb.build()

    # ------------------------------------------------------------ bath 1
    mb = mb_new("BA1_micro", "BATH1")
    mb.push((2.92, 8.35, 0.0), math.pi / 2)
    f2.towel(mb, w=0.46, drop=0.42, key="fabric_cream", bar_z=1.10)
    mb.pop()
    mb.push((3.14, 9.32, 0.862), math.pi / 2)
    f2.toiletries(mb, R(76))
    mb.pop()
    mb.push((4.56, 10.62, 1.455))
    f2.plant_airplant(mb, R(77), n=24, scale=1.0)
    mb.pop()
    mb.push((2.88, 9.70, 1.60), math.pi / 2)
    f2.wall_switch(mb, z=0.0, gangs=1)
    mb.pop()
    mb.build()

    # ------------------------------------------------------------ bath 2
    mb = mb_new("BA2_micro", "BATH2")
    mb.push((0.44, 8.95, 0.0), math.pi / 2)
    f2.towel(mb, w=0.44, drop=0.40, key="fabric_grey", bar_z=1.05)
    mb.pop()
    mb.push((0.44, 9.24, 0.862), math.pi / 2)
    f2.toiletries(mb, R(78))
    mb.pop()
    mb.push((1.42, 10.74, 0.582))
    f2.plant_succulent(mb, R(79), scale=0.6, pot_r=0.10, pot_h=0.12)
    mb.pop()
    mb.build()

    # ------------------------------------------------------------- foyer
    mb = mb_new("FOY_micro", "FOYER")
    mb.push((9.30, 9.42, 0.802), 0.25)
    f2.phone(mb)
    mb.pop()
    mb.push((9.62, 9.50, 0.802))
    f2.plant_airplant(mb, R(80), n=22, scale=0.85)
    mb.pop()
    mb.push((10.95, 10.19, 0.045))
    f2.plant_succulent(mb, R(81), scale=0.62, pot_r=0.10, pot_h=0.12)
    mb.pop()
    mb.push((11.26, 9.62, 1.05), -math.pi / 2)
    f2.wall_switch(mb, z=0.0, gangs=2)
    mb.pop()
    mb.push((11.255, 9.10, 0.30), -math.pi / 2)
    f2.wall_socket(mb, z=0.0, gangs=1)
    mb.pop()
    mb.build()

    # ----------------------------------------------------------- corridor
    mb = mb_new("COR_micro", "CORRIDOR")
    mb.push((6.10, 5.525, 1.05), 0.0)
    f2.wall_switch(mb, z=0.0, gangs=2)
    mb.pop()
    mb.push((8.20, 5.525, 1.05), 0.0)
    f2.wall_switch(mb, z=0.0, gangs=1)
    mb.pop()
    mb.build()

    # ------------------------------------------------------------ balcony
    mb = mb_new("BAL_micro", "BALCONY")
    mb.push((7.55, -2.20, 0.362))
    f2.plant_airplant(mb, R(82), n=26, scale=1.1)
    mb.pop()
    mb.push((9.86, -2.40, 0.362), 0.2)
    f2.books_pile(mb, 3, R(83))
    mb.pop()
    mb.build()

    # -------------------------------------------------------------- stats
    return {"objects": len(made), "names": made}


_result = build()
print(_result, flush=True)