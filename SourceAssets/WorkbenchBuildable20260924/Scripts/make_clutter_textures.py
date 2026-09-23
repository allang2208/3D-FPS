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


def blueprint_sheet(size=1024):
    img = Image.new('RGB', (size, size), (13, 43, 74))
    d = ImageDraw.Draw(img)
    # subtle fibre noise
    noise = Image.effect_noise((size, size), 14).convert('L')
    img = Image.composite(Image.blend(img, Image.new('RGB', (size, size), (30, 60, 90)), 0.25), img, noise.point(lambda p: p // 6))
    d = ImageDraw.Draw(img)
    line = (205, 225, 240)
    faint = (120, 150, 175)
    g = size // 16
    for i in range(1, 16):
        d.line([(i * g, 0), (i * g, size)], fill=faint, width=1)
        d.line([(0, i * g), (size, i * g)], fill=faint, width=1)
    # border
    m = size // 24
    d.rectangle([m, m, size - m, size - m], outline=line, width=3)
    # main view: gear/plate with bolt circle
    cx, cy, r = size * 0.40, size * 0.42, size * 0.22
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=line, width=3)
    d.ellipse([cx - r * .62, cy - r * .62, cx + r * .62, cy + r * .62], outline=line, width=2)
    d.ellipse([cx - r * .18, cy - r * .18, cx + r * .18, cy + r * .18], outline=line, width=3)
    for i in range(8):
        a = i * math.tau / 8
        bx, by = cx + math.cos(a) * r * .82, cy + math.sin(a) * r * .82
        d.ellipse([bx - 9, by - 9, bx + 9, by + 9], outline=line, width=2)
    # teeth
    for i in range(24):
        a = i * math.tau / 24
        d.line([cx + math.cos(a) * r, cy + math.sin(a) * r,
                cx + math.cos(a) * (r + 22), cy + math.sin(a) * (r + 22)], fill=line, width=3)
    # centre cross + dimension lines
    d.line([(cx - r - 40, cy), (cx + r + 40, cy)], fill=faint, width=1)
    d.line([(cx, cy - r - 40), (cx, cy + r + 40)], fill=faint, width=1)
    dy = cy + r + 55
    d.line([(cx - r, dy), (cx + r, dy)], fill=line, width=2)
    for sx in (cx - r, cx + r):
        d.line([(sx, dy - 10), (sx, dy + 10)], fill=line, width=2)
    # side elevation view
    ex, ey = size * 0.74, size * 0.30
    d.rectangle([ex - 90, ey - 60, ex + 90, ey + 60], outline=line, width=3)
    d.line([(ex - 90, ey - 18), (ex + 90, ey - 18)], fill=faint, width=2)
    d.line([(ex - 90, ey + 18), (ex + 90, ey + 18)], fill=faint, width=2)
    d.ellipse([ex - 26, ey - 26, ex + 26, ey + 26], outline=line, width=2)
    # hatched section
    sx0, sy0 = size * 0.70, size * 0.55
    d.rectangle([sx0, sy0, sx0 + 150, sy0 + 110], outline=line, width=2)
    for i in range(0, 260, 14):
        d.line([(sx0 + i, sy0), (sx0, sy0 + i)], fill=faint, width=1)
        d.line([(sx0 + 150, sy0 + i - 110), (sx0 + i - 150 + 110, sy0 + 110)], fill=faint, width=1)
    # title block bottom-right
    tb = [size - m - 300, size - m - 130, size - m, size - m]
    d.rectangle(tb, outline=line, width=3)
    d.line([(tb[0], tb[1] + 46), (tb[2], tb[1] + 46)], fill=line, width=2)
    d.line([(tb[0], tb[1] + 88), (tb[2], tb[1] + 88)], fill=line, width=2)
    d.line([(tb[0] + 150, tb[1]), (tb[0] + 150, tb[3])], fill=line, width=2)
    for row, y in enumerate((tb[1] + 12, tb[1] + 58, tb[1] + 100)):
        w = 120 - row * 30
        d.line([(tb[0] + 14, y), (tb[0] + 14 + w, y)], fill=line, width=4)
        d.line([(tb[0] + 164, y), (tb[0] + 164 + 90, y)], fill=faint, width=3)
    # annotation leaders
    d.line([(cx + r * .62, cy - r * .62), (cx + 180, cy - 210)], fill=line, width=2)
    d.line([(cx + 180, cy - 210), (cx + 260, cy - 210)], fill=line, width=2)
    d.line([(cx - r, cy + r * .3), (cx - 200, cy + 200)], fill=line, width=2)
    d.line([(cx - 200, cy + 200), (cx - 120, cy + 200)], fill=line, width=2)
    # plain paper swatch (top-left corner): sheet edges and scroll end caps sample this
    d.rectangle([0, 0, 44, 44], fill=(238, 233, 216))
    img.save(OUT / 'T_WBKC_Blueprint_BaseColor.png')
    return img


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
