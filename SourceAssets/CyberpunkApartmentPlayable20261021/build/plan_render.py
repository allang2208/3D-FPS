"""Floor-plan render: ceiling and roof hidden, ortho camera just under the slab."""
from __future__ import annotations

import os

import bpy
import numpy as np

OUT = r"D:\CyberpunkApartment\renders\final\plan.png"
HIDE = ("S_ceiling", "S_plate", "DET_ceiling", "DET_pipes", "DET_tray")


def build() -> dict:
    scn = bpy.context.scene
    hidden = []
    for o in scn.objects:
        if o.type == "MESH" and o.name.startswith(HIDE):
            o.hide_render = True
            hidden.append(o.name)
    cam = bpy.data.objects["CAM_plan"]
    cam.location.z = 2.62
    cam.data.clip_start = 0.2
    cam.data.ortho_scale = 17.4
    scn.camera = cam
    scn.render.resolution_x = 1600
    scn.render.resolution_y = 900
    scn.cycles.samples = 220
    scn.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(OUT, check_existing=False)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]
    bpy.data.images.remove(im)
    lum = 0.2126 * a[:, 0] + 0.7152 * a[:, 1] + 0.0722 * a[:, 2]
    stats = {"mean": round(float(lum.mean()), 3),
             "p50": round(float(np.percentile(lum, 50)), 3),
             "dark": round(float((lum <= 0.02).mean()), 3)}
    for name in hidden:
        o = bpy.data.objects.get(name)
        if o:
            o.hide_render = False
    scn.camera = bpy.data.objects["CAM_hero"]
    return {"hidden": hidden, "stats": stats, "kb": os.path.getsize(OUT) // 1024}


_result = build()
print(_result, flush=True)