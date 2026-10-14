"""Generate the desk-clutter textures (blueprint paper, book leather atlas, misc metal/pencil).

Pure PIL/numpy, no engine. Outputs into Authored/Textures/ of this case.
"""
from pathlib import Path
import math, random
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Authored' / 'Textures'
OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(21921)


def blueprint_sheet(size=2048):
    # Keep the established texture identity while authoring engineering paper.
    from engineering_drawings import generate_atlas
    return generate_atlas(OUT)


def books_atlas(size=1024):
    """3x2 grid (PIL coords): row0 red/navy/green leather, row1 text page/pages block/brown."""
    img = Image.new('RGB', (size, size), (250, 245, 230))
    d = ImageDraw.Draw(img)
    H, W = size, size
    cw, ch = W // 3, H // 2
    def leather(x0, y0, x1, y1, base, gilt=True, seed=0):
        r = random.Random(seed)
        d.rectangle([x0, y0, x1, y1], fill=base)
        for _ in range(700):
            px, py = r.uniform(x0, x1), r.uniform(y0, y1)
            s = r.randint(1, 3)
            shade = tuple(max(0, min(255, c + r.randint(-22, 18))) for c in base)
            d.rectangle([px, py, px + s, py + s], fill=shade)
        if gilt:
            for gy in (y0 + (y1 - y0) * .18, y0 + (y1 - y0) * .82):
                d.rectangle([x0 + 6, gy - 4, x1 - 6, gy + 4], fill=(196, 160, 76))
            d.rectangle([x0 + 18, y0 + (y1 - y0) * .44, x1 - 18, y0 + (y1 - y0) * .56], fill=(196, 160, 76))
            for _ in range(50):
                px = r.uniform(x0 + 20, x1 - 20); py = r.uniform(y0 + (y1 - y0) * .44, y0 + (y1 - y0) * .56)
                d.point((px, py), fill=(120, 90, 40))
    leather(0, 0, cw - 4, ch - 4, (122, 34, 32), seed=1)                 # red
    leather(cw + 4, 0, 2 * cw - 4, ch - 4, (38, 56, 96), seed=2)         # navy
    leather(2 * cw + 4, 0, W, ch - 4, (46, 84, 56), seed=3)              # green
    # text page (open book)
    tx0, ty0 = 0, ch + 4
    d.rectangle([tx0, ty0, cw - 4, H], fill=(243, 238, 220))
    for row in range(16):
        y = ty0 + 22 + row * 24
        w = int((cw - 40) * rng.uniform(0.55, 0.95))
        d.line([(tx0 + 18, y), (tx0 + 18 + w, y)], fill=(70, 66, 58), width=3)
    d.rectangle([tx0 + 18, ty0 + 12, cw - 56, ty0 + 18], fill=(120, 40, 36))
    # closed page block
    px0, py0 = cw + 4, ch + 4
    d.rectangle([px0, py0, 2 * cw - 4, H], fill=(238, 231, 208))
    for i in range(0, H - py0, 5):
        d.line([(px0, py0 + i), (2 * cw - 4, py0 + i)], fill=(214, 205, 178), width=1)
    for _ in range(260):
        qx, qy = rng.uniform(px0, 2 * cw - 4), rng.uniform(py0, H)
        d.point((qx, qy), fill=(205, 195, 165))
    # brown leather
    leather(2 * cw + 4, ch + 4, W, H, (88, 60, 38), gilt=False, seed=4)
    img.save(OUT / 'T_WBKC_Books_BaseColor.png')
    return img


def misc_atlas(size=512):
    img = Image.new('RGB', (size, size), (200, 200, 200))
    d = ImageDraw.Draw(img)
    q = size // 2
    # brass tray
    d.rectangle([0, 0, q, q], fill=(176, 138, 62))
    for _ in range(700):
        px, py = rng.uniform(0, q), rng.uniform(0, q)
        d.point((px, py), fill=(150, 116, 50) if rng.random() < .5 else (200, 165, 88))
    # steel
    d.rectangle([q, 0, size, q], fill=(150, 152, 156))
    for i in range(0, size, 3):
        d.line([(q + (i % q), 0), (q + (i % q), q)], fill=(138, 140, 145) if (i // 3) % 2 else (162, 164, 168), width=1)
    # pencil wood + yellow paint
    d.rectangle([0, q, q, size], fill=(222, 178, 110))
    d.rectangle([q, q, size, size], fill=(216, 168, 40))
    for i in range(0, q, 6):
        d.line([(0, q + i), (q, q + i)], fill=(208, 165, 100), width=1)
        d.line([(q + i, q), (q + i, size)], fill=(205, 155, 30), width=1)
    img.save(OUT / 'T_WBKC_Misc_BaseColor.png')
    return img


blueprint_sheet()
books_atlas()
misc_atlas()
print('CLUTTER_TEXTURES_DONE')
