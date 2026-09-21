# Generates the runeBlades quickbar icon in the house style: dark plate, silver
# hexagon frame, azure crystal blade ringed by three orbiting mini-blades.
from PIL import Image, ImageDraw, ImageFilter
import math

W = 1254
img = Image.new('RGB', (W, W), (14, 17, 22))
d = ImageDraw.Draw(img)

def hex_points(cx, cy, r, rot=90):
    return [(cx + r * math.cos(math.radians(rot + 60 * i)),
             cy + r * math.sin(math.radians(rot + 60 * i))) for i in range(6)]

# dark inner plate with a soft vertical sheen
plate = Image.new('RGB', (W, W), (10, 13, 18))
pd = ImageDraw.Draw(plate)
for i, y in enumerate(range(W)):
    t = i / W
    pd.line([(0, y), (W, y)], fill=(int(10 + 10 * t), int(13 + 12 * t), int(18 + 16 * t)))
mask = Image.new('L', (W, W), 0)
ImageDraw.Draw(mask).polygon(hex_points(W/2, W/2, 500), fill=255)
img.paste(plate, (0, 0), mask)

# silver hexagon frame: layered strokes from dark steel to bright edge
for r, col, w in ((512, (58, 62, 68), 10), (500, (150, 158, 168), 26),
                  (500, (206, 214, 224), 8), (486, (96, 102, 112), 6)):
    pts = hex_points(W/2, W/2, r)
    d.line(pts + pts[:1], fill=col, width=w, joint='curve')
# bevel highlight on upper edges
d.line([hex_points(W/2, W/2, 500)[4], hex_points(W/2, W/2, 500)[5]], fill=(232, 238, 246), width=5)

glow = Image.new('RGB', (W, W), (0, 0, 0))
gd = ImageDraw.Draw(glow)

def blade(dd, cx, cy, length, width, angle_deg, body, core):
    """Diamond-section crystal blade pointing +angle; returns polygon."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux
    tip = (cx + ux * length * 0.62, cy + uy * length * 0.62)
    guard_a = (cx - ux * length * 0.30 + px * width * 1.9, cy - uy * length * 0.30 + py * width * 1.9)
    guard_b = (cx - ux * length * 0.30 - px * width * 1.9, cy - uy * length * 0.30 - py * width * 1.9)
    pommel = (cx - ux * length * 0.52, cy - uy * length * 0.52)
    mid_f = (cx + ux * length * 0.18, cy + uy * length * 0.18)
    mid_b = (cx - ux * length * 0.18, cy - uy * length * 0.18)
    dd.polygon([tip, mid_f, guard_a, pommel, guard_b, mid_b], fill=body)
    dd.polygon([tip, (cx + px * width * 0.45, cy + py * width * 0.45), pommel,
                (cx - px * width * 0.45, cy - py * width * 0.45)], fill=core)

# central greatsword, tip up
blade(d, W/2, W/2 + 40, 640, 46, -90, (16, 66, 150), (64, 150, 235))
blade(gd, W/2, W/2 + 40, 640, 46, -90, (10, 40, 110), (60, 170, 255))
# three orbiting mini-blades around the ring, tips facing outward like the skill
for ang, dist in ((-90 + 130, 300), (-90, 330), (-90 - 130, 300)):
    ox = W/2 + 300 * math.cos(math.radians(ang))
    oy = W/2 + 40 + 300 * math.sin(math.radians(ang))
    blade(d, ox, oy, 210, 17, ang, (20, 78, 165), (90, 175, 250))
    blade(gd, ox, oy, 210, 17, ang, (12, 48, 120), (80, 180, 255))

# orbit ring hint (dashed azure circle)
for i in range(36):
    a0 = i * 10 + 2
    pts = [(W/2 + 300 * math.cos(math.radians(a)), W/2 + 40 + 300 * math.sin(math.radians(a)))
           for a in range(a0, a0 + 6, 2)]
    if len(pts) > 1:
        d.line(pts, fill=(24, 60, 110), width=4)
        gd.line(pts, fill=(18, 52, 120), width=4)

glow = glow.filter(ImageFilter.GaussianBlur(14))
from PIL import ImageChops
img = ImageChops.add(img, glow)
img.save(r'D:/FPS3D/FPSGAME/Content/ColdSteelData/Skills/rune_orb_blades.png')
print('icon saved')
