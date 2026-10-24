"""s7 - the city outside: our tower shaft, skyline, signage, traffic, haze.

Coordinate frame: apartment floor is Z = 0, the ground is 152 m below.
"""
from __future__ import annotations

import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402

GROUND = -152.0
FACADES = ["facade_hab", "facade_office", "facade_mega"]
NEONS = ["neon_cyan", "neon_magenta", "neon_pink", "neon_amber", "neon_violet",
         "neon_blue", "neon_green", "neon_white"]


def tower(mb, rng, x, y, w, d, top, key, tiers=2, roof=True, neon=False):
    """One building: stacked slabs with setbacks, roof plant, antenna, beacons."""
    z = GROUND
    for t in range(tiers):
        h = (top - GROUND) * (0.55 if tiers == 2 and t == 0 else
                              (0.42 if tiers == 3 and t == 0 else
                               (0.72 if tiers == 3 and t == 1 else 1.0)))
        if tiers == 2:
            h = (top - GROUND) * (0.62 if t == 0 else 0.38)
        elif tiers == 3:
            h = (top - GROUND) * (0.45 if t == 0 else (0.30 if t == 1 else 0.25))
        if t == tiers - 1:
            h = top - z
        if h <= 1:
            break
        mw = w * (1.0 - 0.14 * t)
        md = d * (1.0 - 0.14 * t)
        mb.box((mw, md, h), (x, y, z + h / 2), key=key)
        # floor bands
        n = max(1, int(h / 3.6))
        if neon or t == 0:
            mb.box((mw + 0.4, md + 0.4, 0.5), (x, y, z + h - 0.25), key="metal_dark")
        z += h
        if t < tiers - 1:
            mb.box((mw + 1.2, md + 1.2, 0.9), (x, y, z + 0.45), key="metal_dark")
    if roof:
        mb.box((w * 0.30, d * 0.30, rng.uniform(2.0, 5.0)),
               (x + rng.uniform(-w * 0.15, w * 0.15), y + rng.uniform(-d * 0.15, d * 0.15), top + 1.5),
               key="metal_dark")
        mb.cyl(0.5, rng.uniform(6, 22), (x, y, top + 8), seg=6, key="metal_steel")
        mb.sphere(0.7, (x, y, top + 8 + rng.uniform(4, 12)), seg=8, rings=5, key="neon_red")
    if neon:
        for sx in (-1, 1):
            mb.box((0.6, 0.6, (top - GROUND) * 0.55),
                   (x + sx * (w / 2 + 0.2), y + d / 2 + 0.2, GROUND + (top - GROUND) * 0.30),
                   key=rng.choice(NEONS))


def billboard(mb, rng, x, y, z, w, h, key=None, frame=True):
    key = key or rng.choice(["holo_panel", "screen_ui", "holo_magenta", "holo_cyan"])
    if frame:
        mb.box((w + 1.2, 0.9, h + 1.2), (x, y - 0.5, z), key="metal_dark")
    mb.plane(w, h, (x, y, z), rot=(0, 0, math.pi), key=key)


def build() -> dict:
    cy.reset_col("CITY")
    rng = random.Random(20771)

    # =====================================================================
    # our own tower: shaft below the balcony, crown above
    # =====================================================================
    mb = cy.MB("CITY_our_tower", "CITY", bevel=0.0)
    mb.box((30.0, 20.0, -GROUND - 0.6), (8.0, 9.0, (GROUND - 0.6) / 2), key="facade_hab")
    # balcony slab fascia + drip
    mb.box((7.6, 0.18, 0.34), (7.64, -2.90, -0.15), key="concrete_raw")
    mb.box((7.8, 0.30, 0.16), (7.64, -2.86, -0.34), key="concrete_raw")
    # parapet above the window + the floor slab above
    mb.box((16.4, 0.60, 1.10), (8.0, -0.32, 3.55), key="facade_hab")
    mb.box((16.6, 3.0, 0.36), (8.0, -1.5, 4.20), key="concrete_raw")
    # crown: keeps rising, so looking up from the balcony reads as a tower
    mb.box((16.4, 11.4, 4.0), (8.0, 5.7, 6.4), key="facade_hab")
    mb.box((14.0, 10.0, 3.0), (8.0, 5.5, 9.9), key="facade_office")
    mb.box((10.0, 8.0, 16.0), (8.0, 5.0, 19.4), key="facade_hab")
    mb.cyl(0.7, 26.0, (8.0, 5.0, 40.0), seg=8, key="metal_steel")
    mb.sphere(0.9, (8.0, 5.0, 54.0), seg=10, rings=6, key="neon_red")
    for i in range(4):
        mb.box((16.4, 0.3, 0.25), (8.0, -0.15, 3.0 + i * 0.12), key="metal_dark")
    # service balcony rail on the left fin
    mb.box((0.3, 20.0, 0.9), (-7.2, 9.0, 3.4), key="metal_dark")
    mb.build()

    # =====================================================================
    # skyline
    # =====================================================================
    mb = cy.MB("CITY_blocks", "CITY", bevel=0.0)
    placed = 0
    # The view axis is -Y from the balcony at X ~ 7.6.  Keep a wide "avenue"
    # open in the middle: near towers sit to the sides and rise above eye
    # level, the middle ground stays below the balcony, the far field is a
    # dense wall of light.
    VIEW_X = 7.6

    # (A) near canyon walls, left and right, rising well above the balcony
    for i in range(18):
        side = -1 if i % 2 == 0 else 1
        k = i // 2
        x = side * (78 + k * 42 + rng.uniform(-9, 9)) + VIEW_X * 0.0
        y = -95 - k * 34 + rng.uniform(-12, 12)
        w = rng.uniform(26, 44)
        d = rng.uniform(26, 44)
        top = rng.uniform(10, 150) - k * 8
        tower(mb, rng, x, y, w, d, top, FACADES[i % 3],
              tiers=rng.choice([2, 2, 3]), neon=(i % 3 == 0))
        placed += 1

    # (B) middle ground: roofs we look down on, plus the odd mid-rise
    for i in range(26):
        x = -150 + i * 12.0 + rng.uniform(-4, 4)
        if abs(x - VIEW_X) < 26:
            continue
        y = -70 - abs(x - VIEW_X) * 0.75 + rng.uniform(-8, 8)
        w = rng.uniform(8, 16)
        d = rng.uniform(8, 16)
        top = rng.uniform(-64, -12)
        tower(mb, rng, x, y, w, d, top, FACADES[i % 3], tiers=1, neon=(i % 2 == 0))
        placed += 1
        mb.box((w * 0.4, d * 0.4, 1.6), (x, y, top + 0.8), key="metal_dark")
        if i % 3 == 0:
            billboard(mb, rng, x, y + d / 2 + 0.6, top + 5.0, rng.uniform(4, 7),
                      rng.uniform(1.6, 2.6), rng.choice(NEONS))

    # (C) the avenue itself: two rows of mid-rises leading the eye outward
    for i in range(14):
        for sgn in (-1, 1):
            x = VIEW_X + sgn * rng.uniform(34, 52)
            y = -120 - i * 46 + rng.uniform(-8, 8)
            w = rng.uniform(14, 22)
            d = rng.uniform(14, 22)
            top = rng.uniform(-46, -4)
            tower(mb, rng, x, y, w, d, top, FACADES[i % 3], tiers=1, neon=(i % 2 == 0))
            placed += 1

    # (D) far skyline wall - dense, tall, tinted
    for i in range(95):
        a = rng.uniform(-1.0, 1.0)
        r = rng.uniform(430, 1150)
        x = VIEW_X + math.sin(a) * r * 0.9
        y = -abs(math.cos(a)) * r
        w = rng.uniform(28, 72)
        d = rng.uniform(28, 72)
        top = rng.uniform(20, 300) * (1.0 - abs(a) * 0.35)
        tower(mb, rng, x, y, w, d, top, FACADES[i % 3], tiers=rng.choice([1, 2, 3]))
        placed += 1

    # (E) hero mega-towers that frame the avenue
    for (x, y, w, d, top, key) in [
        (-118, -205, 54, 54, 175, "facade_mega"),
        (140, -255, 50, 62, 155, "facade_mega"),
        (-260, -430, 70, 70, 265, "facade_mega"),
        (300, -500, 76, 72, 235, "facade_mega"),
    ]:
        tower(mb, rng, x, y, w, d, top, key, tiers=3, neon=True)
        placed += 1
    mb.build()

    # =====================================================================
    # ground: wet streets + street lights + ground traffic
    # =====================================================================
    mb = cy.MB("CITY_ground", "CITY", bevel=0.0)
    mb.box((3000.0, 3000.0, 1.0), (7.0, -700.0, GROUND - 0.5), key="asphalt_wet")
    # the avenue straight ahead
    for i in range(9):
        y = -60 - i * 105
        mb.box((46.0, 6.0, 0.4), (7.0, y, GROUND + 0.2), key="asphalt_wet")
        mb.box((3.0, 6.0, 0.08), (7.0, y, GROUND + 0.44), key="neon_strip_warm")
    # cross streets
    for i in range(9):
        x = -420 + i * 110
        mb.box((5.0, 900.0, 0.4), (x, -540, GROUND + 0.2), key="asphalt_wet")
        mb.box((1.4, 900.0, 0.08), (x + 2.4, -540, GROUND + 0.44), key="neon_strip_cool")
    # street lamps + signals
    for i in range(120):
        x = rng.uniform(-500, 520)
        y = rng.uniform(-760, -40)
        z = GROUND + 9.0
        mb.cyl(0.35, 9.0, (x, y, GROUND + 4.5), seg=5, key="metal_dark")
        mb.sphere(0.9, (x, y, z), seg=6, rings=4,
                  key=rng.choice(["lamp_bulb", "neon_amber", "neon_strip_warm"]))
    # ground traffic
    for i in range(260):
        lane = rng.random()
        if lane < 0.5:
            x = rng.uniform(-460, 500)
            y = -60 - int(rng.uniform(0, 7)) * 105 + rng.choice([-12, 12])
        else:
            x = rng.choice([-420 + int(rng.uniform(0, 8)) * 110]) + rng.choice([-8, 8])
            y = rng.uniform(-700, -50)
        mb.box((2.0, 5.0, 1.6), (x, y, GROUND + 0.9), key="metal_dark")
        mb.box((1.8, 0.3, 0.5), (x, y - 2.6, GROUND + 0.8),
               key="car_headlight" if i % 2 else "car_taillight")
    mb.build()

    # =====================================================================
    # signage on the near towers
    # =====================================================================
    mb = cy.MB("CITY_signs", "CITY", bevel=0.0)
    specs = [
        (-46, -104, -20, 16, 5.5, "neon_magenta"),
        (-58, -122, 22, 12, 30, "holo_panel"),
        (52, -118, -12, 18, 6.0, "neon_cyan"),
        (68, -140, 40, 10, 26, "screen_ui"),
        (-38, -160, 60, 10, 32, "holo_magenta"),
        (44, -186, 78, 12, 34, "neon_amber"),
        (-120, -260, 120, 26, 60, "holo_panel"),
        (140, -300, 150, 30, 70, "screen_ui"),
        (-200, -400, 180, 34, 80, "holo_magenta"),
        (260, -470, 160, 34, 90, "holo_cyan"),
    ]
    for (x, y, z, w, h, key) in specs:
        billboard(mb, rng, x, y, z, w, h, key)
    # vertical blade signs
    for (x, y, z, w, h, key) in [(-34, -96, 4, 3.0, 16, "neon_pink"),
                                 (40, -108, -8, 3.0, 14, "neon_green"),
                                 (-96, -210, 60, 4.0, 22, "neon_violet")]:
        mb.box((w + 0.6, 0.5, h + 0.6), (x, y - 0.3, z), key="metal_dark")
        mb.box((w, 0.2, h), (x, y, z), key=key)
    mb.build()

    # =====================================================================
    # flying traffic
    # =====================================================================
    mb = cy.MB("CITY_traffic", "CITY", bevel=0.0)
    for i in range(90):
        lane_z = rng.choice([-34, -22, -12, -4, 4, 9, 16, 26, 38])
        y = -70 - rng.uniform(0, 620)
        x = rng.uniform(-460, 500)
        ln = rng.uniform(4.0, 7.0)
        mb.box((ln, 2.2, 1.3), (x, y, lane_z), key="metal_dark")
        mb.box((ln * 0.9, 0.4, 0.4), (x, y - 1.1, lane_z + 0.2), key="car_headlight")
        mb.box((ln * 0.9, 0.4, 0.4), (x, y + 1.1, lane_z + 0.2), key="car_taillight")
        # light trail
        mb.box((ln * 9.0, 0.12, 0.12), (x + rng.choice([-1, 1]) * ln * 5.0, y, lane_z - 0.5),
               key="neon_strip_cool" if i % 2 else "neon_strip_warm")
    # a couple of big police-ish cruisers close to the balcony for scale
    for (x, y, z) in [(-26, -46, -6), (34, -58, 12), (-52, -88, 2)]:
        mb.box((9.0, 3.4, 2.0), (x, y, z), key="metal_dark")
        mb.box((8.0, 0.6, 0.6), (x, y - 1.9, z + 0.3), key="neon_red")
        mb.box((8.0, 0.6, 0.6), (x, y + 1.9, z + 0.3), key="neon_blue")
        mb.box((2.0, 1.2, 1.0), (x, y, z + 1.4), key="glass_black")
    mb.build()

    # =====================================================================
    # sky bridges
    # =====================================================================
    mb = cy.MB("CITY_bridges", "CITY", bevel=0.0)
    bridges = [
        ((-72, -190, 60), (52, -118, 40)),
        ((96, -230, 70), (240, -480, 60)),
        ((-72, -190, 120), (-210, -420, 150)),
        ((52, -118, -6), (96, -230, 10)),
    ]
    for (a, b) in bridges:
        x0, y0, z0 = a
        x1, y1, z1 = b
        n = 24
        pts = [((x0 + (x1 - x0) * i / n), (y0 + (y1 - y0) * i / n),
                (z0 + (z1 - z0) * i / n - math.sin(math.pi * i / n) * 6) ) for i in range(n + 1)]
        mb.tube(pts, 3.2, "metal_dark", seg=8)
        for i in range(2, n, 3):
            p = pts[i]
            mb.box((2.0, 2.0, 0.3), (p[0], p[1], p[2] + 3.2), key="neon_strip_cool")
    mb.build()

    # =====================================================================
    # haze volume + horizon glow
    # =====================================================================
    m = bpy.data.materials.get("CITY_fog")
    if not m:
        m = bpy.data.materials.new("CITY_fog")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Density"].default_value = 0.00011
        vol.inputs["Color"].default_value = (0.34, 0.30, 0.50, 1.0)
        vol.inputs["Anisotropy"].default_value = 0.45
        nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me = bpy.data.meshes.new("CITY_fog_mesh")
    xs, ys, zs = (-620, 620), (-1150, -12), (GROUND - 4, 420)
    verts = [(xs[i], ys[j], zs[k]) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new("CITY_fog", me)
    ob.data.materials.append(m)
    cy.col("CITY").objects.link(ob)

    mb = cy.MB("CITY_horizon", "CITY", bevel=0.0)
    # thin far haze band only, well below the horizon line so the sky stays night-dark
    mb.plane(2400, 60, (7.0, -1240, GROUND + 26), rot=(0, 0, 0), key="city_glow")
    mb.build()

    tris = 0
    for o in bpy.data.collections["CITY"].objects:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
    return {"buildings": placed, "objects": len(bpy.data.collections["CITY"].objects),
            "tris": tris}


_result = build()
print(_result, flush=True)