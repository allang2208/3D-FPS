import json
import math
import os
from PIL import Image, ImageDraw

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
OUT = os.path.join(ROOT, "Textures", "detail_v2")
os.makedirs(OUT, exist_ok=True)
RES = {"Canvas": 4096, "Webbing": 4096, "Leather": 4096}
SS = 2

with open(os.path.join(ROOT, "stitch_segments.json"), encoding="utf-8") as f:
    segments = json.load(f)

for mat, res in RES.items():
    segs = segments.get(mat, [])
    s = res * SS
    seam = Image.new("L", (s, s), 0)
    stitch = Image.new("L", (s, s), 0)
    ds = ImageDraw.Draw(seam)
    dt = ImageDraw.Draw(stitch)
    seam_w = max(2, round(2.4 * res / 2048 * SS))
    stitch_w = max(1, round(1.15 * res / 2048 * SS))
    dash_len = max(2, round(4.0 * res / 2048 * SS))
    spacing = max(4, round(6.5 * res / 2048 * SS))
    offset = max(2, round(2.2 * res / 2048 * SS))
    for seg in segs:
        u1, v1, u2, v2 = seg
        x1, y1 = u1 * s, (1.0 - v1) * s
        x2, y2 = u2 * s, (1.0 - v2) * s
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 2:
            continue
        ds.line([(x1, y1), (x2, y2)], fill=255, width=seam_w)
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        t = spacing * 0.5
        while t < length:
            cx, cy = x1 + ux * t, y1 + uy * t
            for side in (-1.0, 1.0):
                sx = cx + px * offset * side
                sy = cy + py * offset * side
                dt.line(
                    [(sx - ux * dash_len * 0.5, sy - uy * dash_len * 0.5),
                     (sx + ux * dash_len * 0.5, sy + uy * dash_len * 0.5)],
                    fill=255, width=stitch_w)
            t += spacing
    seam = seam.resize((res, res), Image.LANCZOS)
    stitch = stitch.resize((res, res), Image.LANCZOS)
    seam.save(os.path.join(OUT, "seam_%s.png" % mat))
    stitch.save(os.path.join(OUT, "stitch_%s.png" % mat))
    print("ALICE_MASK", mat, "segments", len(segs), "seam_px", seam_w, "stitch_px", stitch_w)
