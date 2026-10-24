"""s9 — cameras. Hero, wide, balcony, city, room shots, plus an ortho plan."""
from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402

CAMS = [
    # name, location, target, lens, fstop, focus_obj_or_None, sensor_fit
    ("CAM_hero", (10.55, 4.95, 1.42), (6.60, -2.20, 1.30), 24, 5.6, None),
    ("CAM_wide", (10.85, 5.05, 2.02), (4.90, -1.30, 1.05), 19, 8.0, None),
    ("CAM_balcony", (9.90, -2.35, 1.55), (6.20, 3.40, 1.35), 22, 4.0, None),
    ("CAM_city", (7.62, 3.10, 1.45), (7.62, -40.0, 1.10), 32, 8.0, None),
    # the vista: out on the balcony deck, wide lens, city below and beyond
    ("CAM_night", (7.30, -1.45, 1.66), (8.40, -260.0, 9.00), 17, 11.0, None),
    ("CAM_vista", (5.20, -2.45, 1.35), (14.00, -200.0, 24.00), 20, 11.0, None),
    ("CAM_down", (8.60, -2.50, 1.30), (6.00, -42.0, -120.0), 24, 11.0, None),
    ("CAM_lounge", (4.70, 4.20, 1.30), (10.60, -1.40, 1.45), 22, 4.0, None),
    ("CAM_master", (3.30, 4.90, 1.55), (0.90, 0.60, 1.05), 20, 4.0, None),
    ("CAM_kitchen", (5.22, 7.05, 1.66), (7.30, 10.35, 1.00), 20, 4.0, None),
    ("CAM_bed2", (11.85, 1.10, 1.60), (15.20, 4.40, 1.00), 20, 4.0, None),
    ("CAM_bed3", (12.10, 8.60, 1.62), (15.30, 6.30, 1.15), 22, 4.0, None),
    ("CAM_bath", (3.30, 8.55, 1.65), (3.90, 10.40, 1.00), 18, 5.6, None),
    ("CAM_foyer", (9.24, 7.16, 1.56), (10.55, 10.50, 1.42), 20, 5.6, None),
    ("CAM_corridor", (2.30, 6.30, 1.55), (11.20, 6.10, 1.28), 22, 8.0, None),
    # macro detail shots: these exist to show the modelling, not the room
    ("CAM_macro_plant", (6.02, 1.34, 1.06), (5.14, 0.58, 0.78), 68, 9.0, None),
    ("CAM_macro_desk", (13.86, 1.62, 1.18), (13.26, 0.70, 0.78), 58, 9.0, None),
    ("CAM_macro_bath", (3.10, 9.40, 1.52), (3.88, 10.86, 1.28), 46, 11.0, None),
]

PLAN_CAM = ("CAM_plan", (8.0, 5.5, 26.0), (8.0, 5.5, 0.0), 50)


def build() -> dict:
    cy.reset_col("CAMS")
    made = []
    for name, loc, tgt, lens, fstop, focus in CAMS:
        cd = bpy.data.cameras.get(name + "_data") or bpy.data.cameras.new(name + "_data")
        cd.lens = lens
        cd.sensor_width = 36.0
        cd.clip_start = 0.05
        cd.clip_end = 3000.0
        ob = bpy.data.objects.get(name)
        if ob is None:
            ob = bpy.data.objects.new(name, cd)
        else:
            ob.data = cd
        cy.col("CAMS").objects.link(ob)
        ob.location = loc
        d = Vector(tgt) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        # DOF
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = max(0.4, d.length)
        if focus:
            cd.dof.focus_object = bpy.data.objects.get(focus)
        made.append(name)

    # plan camera (orthographic, straight down)
    name, loc, tgt, lens = PLAN_CAM
    cd = bpy.data.cameras.new(name + "_data")
    cd.type = "ORTHO"
    cd.ortho_scale = 18.0
    cd.clip_start = 1.0
    cd.clip_end = 100.0
    ob = bpy.data.objects.new(name, cd)
    cy.col("CAMS").objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (0.0, 0.0, 0.0)
    made.append(name)

    scn = bpy.context.scene
    scn.camera = bpy.data.objects.get("CAM_hero")
    return {"cameras": made, "active": scn.camera.name if scn.camera else None}


_result = build()
print(_result, flush=True)