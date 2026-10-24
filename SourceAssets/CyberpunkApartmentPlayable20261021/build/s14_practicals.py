"""s14 -- practical light fixtures: desk lamp, mirror light, under-cabinet fills.

These exist because the macro cameras (and the room shots) need real light
sources where the modelling detail is; they are also the honest way to light
an interior.
"""
from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402
import furn  # noqa: E402

OBJ = "DET_practicals"


def add_light(name, kind, loc, energy, color, size=1.0, rot=None, spread=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.shape = "RECTANGLE"
        ld.size = size
    if kind in ("SPOT", "POINT"):
        if kind == "SPOT":
            ld.spot_size = math.radians(spread or 60)
    if kind == "POINT":
        ld.shadow_soft_size = 0.03
    ob = bpy.data.objects.new(name, ld)
    cy.col("LIGHTS").objects.link(ob)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    return ob


def build():
    for n in ("DET_practicals",):
        for ob in list(bpy.data.objects):
            if ob.name == n or ob.name.startswith(n + "."):
                bpy.data.objects.remove(ob, do_unlink=True)
    for ln in ("L_desk_lamp", "L_mirror_bar", "L_cab_a", "L_cab_b",
               "L_master_floor", "L_bed2_floor", "L_bed3_floor"):
        for ob in list(bpy.data.objects):
            if ob.name == ln or ob.name.startswith(ln + "."):
                bpy.data.objects.remove(ob, do_unlink=True)

    cy.col("DETAILS")
    mb = cy.MB(OBJ, "DETAILS", bevel=0.001)

    # ------------------------------------------------------- desk lamp
    mb.push((12.44, 0.95, 0.742))
    furn.lathe(mb, [(0.0, 0.0), (0.055, 0.0), (0.058, 0.008), (0.050, 0.016),
                    (0.020, 0.026), (0.0, 0.028)], seg=28, key="metal_black")
    # lower arm leaning in, upper arm out over the desk
    furn.stem(mb, [(0.0, 0.0, 0.026), (0.010, -0.020, 0.220), (0.028, -0.055, 0.400)],
              r=0.0075, key="metal_black", seg=8, taper=0.15)
    mb.sphere(0.014, (0.028, -0.055, 0.400), seg=14, rings=8, key="metal_brushed")
    furn.stem(mb, [(0.028, -0.055, 0.400), (0.150, -0.120, 0.470), (0.255, -0.190, 0.440)],
              r=0.0070, key="metal_black", seg=8, taper=0.15)
    mb.sphere(0.016, (0.255, -0.190, 0.440), seg=14, rings=8, key="metal_brushed")
    # conical shade, open downward
    furn.lathe(mb, [(0.0, 0.075), (0.020, 0.072), (0.030, 0.050), (0.072, 0.008),
                    (0.078, 0.0), (0.074, -0.004), (0.066, 0.004), (0.026, 0.046),
                    (0.0, 0.046)], loc=(0.255, -0.222, 0.400),
               rot=(0.45, 0, 0), seg=30, key="paint_charcoal")
    furn.lathe(mb, [(0.0, 0.0), (0.058, 0.0), (0.0, 0.002)], loc=(0.255, -0.222, 0.398),
               rot=(0.45, 0, 0), seg=24, key="lamp_bulb")
    mb.pop()

    # --------------------------------------------------- mirror light bar
    mb.push((3.14, 8.965, 2.045), 0.0)
    mb.box((0.94, 0.055, 0.028), (0, 0, 0), key="metal_brushed")
    mb.box((0.90, 0.020, 0.014), (0, 0.032, 0.0), key="lamp_bulb")
    for sxx in (-1, 1):
        mb.box((0.028, 0.040, 0.048), (sxx * 0.455, 0.012, 0.006), key="metal_brushed")
    mb.pop()

    # ------------------------------------------- under-cabinet task lights
    for x in (5.75, 7.15):
        mb.push((x, 10.60, 1.505))
        mb.box((0.90, 0.035, 0.016), (0, 0, 0), key="metal_brushed")
        mb.box((0.86, 0.014, 0.008), (0, 0, -0.011), key="neon_strip_warm")
        mb.pop()

    mb.build()

    add_light("L_desk_lamp", "POINT", (12.70, 0.76, 1.15), 70.0, (1.0, 0.86, 0.68))
    add_light("L_mirror_bar", "AREA", (3.14, 8.94, 1.96), 110.0, (1.0, 0.92, 0.86),
              size=0.90, rot=(math.radians(-12), 0, 0))
    # low floor bounce in the bedrooms: no visible source, just the light a
    # concrete floor would give back at this exposure
    for name, loc, e, col in (
            ("L_master_floor", (1.60, 2.80, 0.45), 20.0, (0.72, 0.80, 1.0)),
            ("L_bed2_floor", (13.60, 3.10, 0.45), 24.0, (0.70, 0.80, 1.0)),
            ("L_bed3_floor", (13.60, 8.10, 0.45), 20.0, (0.74, 0.78, 1.0))):
        ob = add_light(name, "POINT", loc, e, col)
        ob.data.shadow_soft_size = 0.85

    add_light("L_cab_a", "POINT", (5.75, 10.52, 1.44), 34.0, (1.0, 0.82, 0.62))
    add_light("L_cab_b", "POINT", (7.15, 10.52, 1.44), 34.0, (1.0, 0.82, 0.62))

    ob = bpy.data.objects[OBJ]
    ob.data.calc_loop_triangles()
    return {"object": OBJ, "tris": len(ob.data.loop_triangles),
            "lights": [o.name for o in bpy.data.collections["LIGHTS"].objects]}


_result = build()
print(_result["object"], _result["tris"], "lights", len(_result["lights"]), flush=True)