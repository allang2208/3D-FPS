"""Final quality renders (run through _setup/run.py so the 30 s addon cap is bypassed)."""
from __future__ import annotations

import os
import time

import bpy
import numpy as np

SET = open(r"D:\CyberpunkApartment\_setup\final_set.txt").read().strip() or "a"
OUT = r"D:\CyberpunkApartment\renders\final"

SETS = {
    "a": ["CAM_hero", "CAM_wide", "CAM_lounge", "CAM_balcony", "CAM_master",
          "CAM_kitchen", "CAM_bed2"],
    "b": ["CAM_bed3", "CAM_bath", "CAM_foyer", "CAM_corridor", "CAM_night",
          "CAM_vista", "CAM_city", "CAM_plan"],
    "c": ["CAM_macro_plant", "CAM_macro_desk", "CAM_macro_bath"],
}


def build() -> dict:
    scn = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    scn.render.resolution_x = 1920
    scn.render.resolution_y = 1080
    scn.render.resolution_percentage = 100
    scn.cycles.samples = 300
    scn.cycles.use_adaptive_sampling = True
    scn.cycles.adaptive_threshold = 0.012
    scn.cycles.filter_width = 1.2
    rows = []
    if SETS.get(SET) is None:
        SETS[SET] = [n.strip() for n in SET.split(',') if n.strip()]
        SETS[SET] = [n if n.startswith('CAM_') else 'CAM_' + n for n in SETS[SET]]
    for name in SETS[SET]:
        cam = bpy.data.objects.get(name)
        if cam is None:
            rows.append([name, "missing"])
            continue
        scn.camera = cam
        p = os.path.join(OUT, name.replace("CAM_", "") + ".png")
        scn.render.filepath = p
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = round(time.time() - t0, 1)
        im = bpy.data.images.load(p, check_existing=False)
        a = np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]
        bpy.data.images.remove(im)
        lum = 0.2126 * a[:, 0] + 0.7152 * a[:, 1] + 0.0722 * a[:, 2]
        sat = a.max(axis=1) - a.min(axis=1)
        rows.append([name.split("_")[1], dt,
                     round(float(lum.mean()), 3),
                     round(float(np.percentile(lum, 50)), 3),
                     round(float(np.percentile(lum, 95)), 3),
                     round(float((lum <= 0.02).mean()), 3),
                     round(float((lum >= 0.98).mean()), 4),
                     round(float(sat.mean()), 3),
                     os.path.getsize(p) // 1024])
    scn.camera = bpy.data.objects["CAM_hero"]
    return {"set": SET, "rows": rows}


_result = build()
print("FINAL|" + "|".join(str(x) for x in _result["rows"]), flush=True)