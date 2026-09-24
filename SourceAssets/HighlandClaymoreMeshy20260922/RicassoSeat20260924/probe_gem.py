"""Locate the teal guard gem on the original blade and guard."""
import json
from pathlib import Path
import bpy
import numpy as np
P = Path(__file__).resolve().parent
SOURCE = P.parent / "Integration" / "HighlandClaymore_Modular_Editable.blend"
TEX = P.parent / "Meshy" / "candidate01" / "downloads" / "texture_0.png"
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
tex = bpy.data.images.load(str(TEX))
w, h = tex.size
raw = np.array(tex.pixels[:], dtype=np.float32).reshape(h, w, 4)
image = (raw[:, :, :3] * 255).astype(np.uint8)
image = np.flipud(image)
report = {}
for name in ("SM_Highland_Blade_factory", "SM_Highland_Guard_factory"):
    obj = bpy.data.objects[name]
    mesh = obj.data
    uv = mesh.uv_layers.active.data
    hits = []
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            u, v = uv[li].uv
            x = int(np.clip(u, 0, 0.999) * (w - 1))
            y = int(np.clip(1 - v, 0, 0.999) * (h - 1))
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            r, g, b = (int(image[y, x, 0]), int(image[y, x, 1]), int(image[y, x, 2]))
            if b > r + 40 and b > 110 and 40 < g < 180 and abs(co.x) < 0.018 and -0.03 < co.z < 0.04:
                hits.append((co.x, co.y, co.z))
    arr = np.array(hits) if hits else np.zeros((0, 3))
    report[name] = {
        "teal_loops": int(len(hits)),
        "cm": None if len(arr) == 0 else {
            "x": [round(float(arr[:, 0].min()) * 100, 2), round(float(arr[:, 0].max()) * 100, 2)],
            "y": [round(float(arr[:, 1].min()) * 100, 2), round(float(arr[:, 1].max()) * 100, 2)],
            "z": [round(float(arr[:, 2].min()) * 100, 2), round(float(arr[:, 2].max()) * 100, 2)],
        },
    }
out = P / "probe_gem.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("PROBE_GEM", out)
