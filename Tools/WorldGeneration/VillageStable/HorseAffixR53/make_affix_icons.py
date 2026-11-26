"""
Generate 20 ColdSteel-style RGBA PNG icons (256x256, 4x supersampled) for the
HillsVillageStable Horse Affix System, plus a labeled 5x4 contact sheet for review.

Output icons:
  d:/FPS3D/FPSGAME/Content/ColdSteelData/Icons/HorseAffixes/<affix_id>.png
Contact sheet:
  F:/FPSGAMEData/ArtReviews/HillsVillageStable/HorseAffixAndBagR53-20261126/affix_icons_sheet.png
"""
import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path(r"d:/FPS3D/FPSGAME/Content/ColdSteelData/Icons/HorseAffixes")
REVIEW_DIR = Path(r"F:/FPSGAMEData/ArtReviews/HillsVillageStable/HorseAffixAndBagR53-20261126")
SIZE = 256
SS = 4  # 1024x1024 supersampled canvas -> 256x256 Lanczos
W = SIZE * SS
CX = W / 2.0
CY = W / 2.0

# ColdSteel palette (tiers: pos2, pos1, neg1, neg2, special_*)
THEMES = {
    "pos2": {
        "bg0": (14, 30, 26, 255),
        "bg1": (26, 62, 50, 255),
        "glow": (96, 232, 168, 120),
        "rim": (122, 236, 178, 255),
        "rim_inner": (224, 212, 152, 220),
        "fg": (228, 252, 238, 255),
        "accent": (236, 206, 128, 255),
        "shadow": (6, 16, 14, 210),
    },
    "pos1": {
        "bg0": (15, 26, 24, 255),
        "bg1": (24, 48, 42, 255),
        "glow": (72, 198, 142, 95),
        "rim": (92, 204, 148, 255),
        "rim_inner": (160, 228, 192, 170),
        "fg": (214, 242, 228, 255),
        "accent": (118, 226, 168, 255),
        "shadow": (7, 14, 13, 210),
    },
    "neg1": {
        "bg0": (28, 16, 19, 255),
        "bg1": (54, 24, 30, 255),
        "glow": (212, 86, 98, 95),
        "rim": (210, 96, 108, 255),
        "rim_inner": (238, 154, 162, 155),
        "fg": (246, 212, 216, 255),
        "accent": (232, 108, 118, 255),
        "shadow": (18, 7, 9, 220),
    },
    "neg2": {
        "bg0": (32, 12, 16, 255),
        "bg1": (68, 20, 28, 255),
        "glow": (235, 68, 86, 125),
        "rim": (236, 82, 96, 255),
        "rim_inner": (255, 168, 146, 185),
        "fg": (252, 216, 212, 255),
        "accent": (248, 114, 96, 255),
        "shadow": (20, 5, 8, 230),
    },
    "special_gold": {
        "bg0": (26, 22, 14, 255),
        "bg1": (58, 45, 24, 255),
        "glow": (236, 192, 96, 135),
        "rim": (232, 196, 114, 255),
        "rim_inner": (255, 236, 178, 215),
        "fg": (252, 240, 208, 255),
        "accent": (242, 196, 98, 255),
        "shadow": (18, 13, 6, 230),
    },
    "special_war": {
        "bg0": (32, 17, 15, 255),
        "bg1": (66, 34, 24, 255),
        "glow": (242, 144, 78, 135),
        "rim": (234, 190, 106, 255),
        "rim_inner": (255, 164, 118, 205),
        "fg": (254, 234, 214, 255),
        "accent": (245, 122, 92, 255),
        "shadow": (20, 9, 7, 230),
    },
    "special_arcane": {
        "bg0": (17, 22, 36, 255),
        "bg1": (36, 46, 78, 255),
        "glow": (122, 186, 255, 140),
        "rim": (228, 196, 118, 255),
        "rim_inner": (146, 214, 255, 210),
        "fg": (230, 244, 255, 255),
        "accent": (124, 202, 255, 255),
        "shadow": (9, 12, 24, 230),
    },
    "special_stamina": {
        "bg0": (14, 28, 34, 255),
        "bg1": (26, 60, 70, 255),
        "glow": (96, 228, 218, 140),
        "rim": (230, 196, 114, 255),
        "rim_inner": (132, 242, 228, 210),
        "fg": (232, 254, 250, 255),
        "accent": (108, 238, 218, 255),
        "shadow": (7, 16, 20, 230),
    },
}


def make_base_medallion(theme_key: str, special: bool = False) -> Image.Image:
    t = THEMES[theme_key]
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    px = img.load()
    margin = int(W * 0.055)
    rad = int(W * 0.16)

    # Rounded square mask
    mask = Image.new("L", (W, W), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([margin, margin, W - margin, W - margin], radius=rad, fill=255)

    # Radial gradient background inside rounded square
    bg = Image.new("RGBA", (W, W), t["bg0"])
    bdraw = ImageDraw.Draw(bg)
    # Soft radial glow in center using concentric circles
    steps = 48
    max_r = W * 0.56
    for i in range(steps, 0, -1):
        frac = i / steps
        r = max_r * frac
        mix = (1.0 - frac) ** 1.45
        col = tuple(
            int(t["bg0"][c] * (1.0 - mix) + t["bg1"][c] * mix) for c in range(3)
        ) + (255,)
        bdraw.ellipse([CX - r, CY - r * 1.05 - W * 0.04, CX + r, CY + r * 0.95 - W * 0.04], fill=col)

    # Central subtle glow
    glow_layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    gr = W * 0.30
    gd.ellipse([CX - gr, CY - gr, CX + gr, CY + gr], fill=t["glow"])
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=W * 0.09))
    bg = Image.alpha_composite(bg, glow_layer)

    # Top subtle metallic sheen
    sheen = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.ellipse([W * 0.12, -W * 0.18, W * 0.88, W * 0.36], fill=(255, 255, 255, 28))
    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=W * 0.04))
    bg = Image.alpha_composite(bg, sheen)

    img.paste(bg, (0, 0), mask)
    draw = ImageDraw.Draw(img)

    # Outer rim border
    bw = int(W * (0.030 if special else 0.024))
    draw.rounded_rectangle(
        [margin, margin, W - margin, W - margin],
        radius=rad,
        outline=t["rim"],
        width=bw,
    )
    # Inner hairline frame
    inset = margin + bw + int(W * 0.014)
    draw.rounded_rectangle(
        [inset, inset, W - inset, W - inset],
        radius=max(8, rad - bw - 8),
        outline=t["rim_inner"],
        width=int(W * 0.008),
    )

    if special:
        # Four heraldic corner diamonds for special affixes
        d = int(W * 0.036)
        c_off = inset + int(W * 0.046)
        for sx, sy in [(c_off, c_off), (W - c_off, c_off), (c_off, W - c_off), (W - c_off, W - c_off)]:
            pts = [(sx, sy - d), (sx + d, sy), (sx, sy + d), (sx - d, sy)]
            draw.polygon(pts, fill=t["rim"])
    return img


def poly_pts(norm_pts):
    return [(x * W, y * W) for (x, y) in norm_pts]


def heart_polygon(cx, cy, scale, n=72):
    pts = []
    for i in range(n):
        th = 2.0 * math.pi * i / n
        x = 16.0 * (math.sin(th) ** 3)
        y = -(13.0 * math.cos(th) - 5.0 * math.cos(2 * th) - 2.0 * math.cos(3 * th) - math.cos(4 * th))
        pts.append((cx + x * scale, cy + y * scale))
    return pts


def draw_with_shadow(base: Image.Image, draw_fn, shadow_col):
    fg = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(fg))
    # Build drop shadow from fg alpha
    alpha = fg.split()[3]
    sh = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    solid = Image.new("RGBA", (W, W), shadow_col)
    sh.paste(solid, (0, int(W * 0.022)), alpha)
    sh = sh.filter(ImageFilter.GaussianBlur(radius=W * 0.020))
    out = Image.alpha_composite(base, sh)
    out = Image.alpha_composite(out, fg)
    return out


def draw_chevron(d: ImageDraw.Draw, cx, cy, w, h, up, col, stroke):
    sign = 1 if up else -1
    pts = [(cx - w, cy + sign * h * 0.5), (cx, cy - sign * h * 0.5), (cx + w, cy + sign * h * 0.5)]
    d.line(pts, fill=col, width=stroke, joint="curve")


def draw_shield(d: ImageDraw.Draw, cx, cy, sx, sy, fill, outline, width):
    pts = [
        (cx, cy - sy),
        (cx + sx * 0.88, cy - sy * 0.68),
        (cx + sx * 0.78, cy + sy * 0.16),
        (cx, cy + sy),
        (cx - sx * 0.78, cy + sy * 0.16),
        (cx - sx * 0.88, cy - sy * 0.68),
    ]
    d.polygon(pts, fill=fill, outline=outline)
    d.line(pts + [pts[0]], fill=outline, width=width, joint="curve")


def draw_horseshoe(d: ImageDraw.Draw, cx, cy, r_out, r_in, col, accent, cracked=False):
    # Draw thick U-shaped arch opening downwards
    pts_out = []
    pts_in = []
    steps = 40
    start_deg = 148
    end_deg = 392
    for i in range(steps + 1):
        ang = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        pts_out.append((cx + math.cos(ang) * r_out, cy + math.sin(ang) * r_out))
    for i in range(steps, -1, -1):
        ang = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        pts_in.append((cx + math.cos(ang) * r_in, cy + math.sin(ang) * r_in))
    d.polygon(pts_out + pts_in, fill=col)
    # Nail holes
    for deg in [180, 215, 250, 290, 325, 360]:
        ang = math.radians(deg)
        rm = (r_out + r_in) * 0.5
        nx = cx + math.cos(ang) * rm
        ny = cy + math.sin(ang) * rm
        nr = (r_out - r_in) * 0.19
        d.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=accent)
    if cracked:
        # Dark fracture zig-zag across right shoulder
        d.line(
            [
                (cx + r_out * 0.10, cy - r_out * 1.05),
                (cx + r_out * 0.28, cy - r_out * 0.62),
                (cx + r_out * 0.08, cy - r_out * 0.34),
                (cx + r_out * 0.34, cy - r_out * 0.06),
            ],
            fill=(24, 8, 12, 255),
            width=int(W * 0.026),
        )


def draw_bag_silhouette(d: ImageDraw.Draw, cx, cy, bw, bh, fill, accent, strap):
    # Main saddlebag body
    left, top, right, bot = cx - bw, cy - bh * 0.65, cx + bw, cy + bh
    d.rounded_rectangle([left, top, right, bot], radius=int(bw * 0.28), fill=fill)
    # Top flap
    flap = [
        (left - bw * 0.06, top),
        (right + bw * 0.06, top),
        (right + bw * 0.02, cy + bh * 0.02),
        (cx, cy + bh * 0.22),
        (left - bw * 0.02, cy + bh * 0.02),
    ]
    d.polygon(flap, fill=accent)
    # Handle arch on top
    hw = bw * 0.42
    d.arc([cx - hw, top - bh * 0.52, cx + hw, top + bh * 0.25], 180, 360, fill=strap, width=int(W * 0.032))
    # Two vertical straps + brass buckles
    for sx in [cx - bw * 0.46, cx + bw * 0.46]:
        sw = bw * 0.13
        d.rectangle([sx - sw, top + bh * 0.05, sx + sw, bot - bh * 0.12], fill=strap)
        d.rounded_rectangle(
            [sx - sw * 1.45, cy - bh * 0.02, sx + sw * 1.45, cy + bh * 0.26],
            radius=int(sw * 0.5),
            fill=accent,
            outline=fill,
            width=int(W * 0.010),
        )


def draw_horse_head(d: ImageDraw.Draw, cx, cy, s, col, accent):
    # Stylized heraldic horse head facing right
    pts = [
        (cx - 0.36 * s, cy + 0.52 * s),
        (cx - 0.34 * s, cy + 0.06 * s),
        (cx - 0.26 * s, cy - 0.34 * s),
        (cx - 0.10 * s, cy - 0.52 * s),
        (cx - 0.04 * s, cy - 0.72 * s),  # ear tip
        (cx + 0.08 * s, cy - 0.50 * s),
        (cx + 0.28 * s, cy - 0.34 * s),
        (cx + 0.50 * s, cy - 0.06 * s),  # bridge of nose
        (cx + 0.46 * s, cy + 0.10 * s),  # muzzle
        (cx + 0.30 * s, cy + 0.16 * s),
        (cx + 0.16 * s, cy + 0.06 * s),  # jaw
        (cx + 0.10 * s, cy + 0.22 * s),
        (cx + 0.22 * s, cy + 0.52 * s),
    ]
    d.polygon(pts, fill=col)
    # Flowing mane spikes on left
    for i in range(4):
        my = cy - 0.34 * s + i * 0.20 * s
        d.polygon(
            [(cx - 0.28 * s, my), (cx - 0.52 * s, my + 0.08 * s), (cx - 0.32 * s, my + 0.18 * s)],
            fill=accent,
        )
    # Fierce eye
    d.polygon(
        [(cx + 0.06 * s, cy - 0.24 * s), (cx + 0.20 * s, cy - 0.20 * s), (cx + 0.10 * s, cy - 0.14 * s)],
        fill=(18, 12, 10, 255),
    )


def make_icon(affix_id: str) -> Image.Image:
    # 1. very_strong
    if affix_id == "very_strong":
        t = THEMES["pos2"]
        base = make_base_medallion("pos2")
        def fg(d):
            draw_shield(d, CX, CY + W * 0.06, W * 0.25, W * 0.27, t["fg"], t["accent"], int(W * 0.022))
            d.polygon(heart_polygon(CX, CY + W * 0.06, W * 0.0082), fill=t["bg1"])
            d.polygon(heart_polygon(CX, CY + W * 0.06, W * 0.0058), fill=t["accent"])
            draw_chevron(d, CX, CY - W * 0.25, W * 0.13, W * 0.055, True, t["accent"], int(W * 0.026))
            draw_chevron(d, CX, CY - W * 0.33, W * 0.095, W * 0.045, True, t["fg"], int(W * 0.022))
        return draw_with_shadow(base, fg, t["shadow"])

    # 2. strong
    if affix_id == "strong":
        t = THEMES["pos1"]
        base = make_base_medallion("pos1")
        def fg(d):
            draw_shield(d, CX, CY + W * 0.05, W * 0.24, W * 0.27, t["fg"], t["accent"], int(W * 0.020))
            d.polygon(heart_polygon(CX, CY + W * 0.05, W * 0.0065), fill=t["bg1"])
            draw_chevron(d, CX, CY - W * 0.28, W * 0.12, W * 0.055, True, t["accent"], int(W * 0.025))
        return draw_with_shadow(base, fg, t["shadow"])

    # 3. frail
    if affix_id == "frail":
        t = THEMES["neg1"]
        base = make_base_medallion("neg1")
        def fg(d):
            d.polygon(heart_polygon(CX, CY + W * 0.01, W * 0.0145), fill=t["fg"])
            # Fracture line down center
            d.line(
                [(CX + W * 0.03, CY - W * 0.16), (CX - W * 0.04, CY - W * 0.02), (CX + W * 0.05, CY + W * 0.08), (CX - W * 0.03, CY + W * 0.24)],
                fill=t["bg0"],
                width=int(W * 0.030),
            )
            draw_chevron(d, CX, CY + W * 0.31, W * 0.10, W * 0.05, False, t["accent"], int(W * 0.024))
        return draw_with_shadow(base, fg, t["shadow"])

    # 4. very_frail
    if affix_id == "very_frail":
        t = THEMES["neg2"]
        base = make_base_medallion("neg2")
        def fg(d):
            # Split heart halves pulled slightly apart
            left_pts = [(x - W * 0.035, y) for (x, y) in heart_polygon(CX, CY - W * 0.02, W * 0.014) if x <= CX + W * 0.01]
            right_pts = [(x + W * 0.035, y) for (x, y) in heart_polygon(CX, CY - W * 0.02, W * 0.014) if x >= CX - W * 0.01]
            d.polygon(left_pts, fill=t["fg"])
            d.polygon(right_pts, fill=t["accent"])
            draw_chevron(d, CX, CY + W * 0.24, W * 0.12, W * 0.055, False, t["fg"], int(W * 0.024))
            draw_chevron(d, CX, CY + W * 0.33, W * 0.12, W * 0.055, False, t["accent"], int(W * 0.024))
        return draw_with_shadow(base, fg, t["shadow"])

    # 5. fleet_footed
    if affix_id == "fleet_footed":
        t = THEMES["pos2"]
        base = make_base_medallion("pos2")
        def fg(d):
            # Sleek tapered sweeping pegasus wing feathers behind winged horseshoe
            feathers = [
                [(0.14, 0.27), (0.50, 0.37), (0.43, 0.43), (0.19, 0.36)],
                [(0.16, 0.39), (0.47, 0.47), (0.40, 0.53), (0.21, 0.47)],
                [(0.21, 0.51), (0.45, 0.56), (0.39, 0.61), (0.26, 0.58)],
            ]
            for i, f in enumerate(feathers):
                d.polygon(poly_pts(f), fill=t["accent"] if i == 0 else t["rim"])
            draw_horseshoe(d, CX + W * 0.12, CY + W * 0.04, W * 0.205, W * 0.12, t["fg"], t["bg0"])
            d.line([(CX - W * 0.30, CY + W * 0.27), (CX + W * 0.24, CY + W * 0.27)], fill=t["accent"], width=int(W * 0.024))
            d.line([(CX - W * 0.18, CY + W * 0.34), (CX + W * 0.30, CY + W * 0.34)], fill=t["fg"], width=int(W * 0.018))
        return draw_with_shadow(base, fg, t["shadow"])

    # 6. swift
    if affix_id == "swift":
        t = THEMES["pos1"]
        base = make_base_medallion("pos1")
        def fg(d):
            # Sleek arrow-wind arcs + horseshoe
            for i, (x0, y0, l) in enumerate([(0.16, 0.34, 0.26), (0.14, 0.48, 0.30), (0.20, 0.62, 0.24)]):
                d.line([(x0 * W, y0 * W), ((x0 + l) * W, y0 * W)], fill=t["accent"], width=int(W * 0.026))
            draw_horseshoe(d, CX + W * 0.12, CY + W * 0.02, W * 0.20, W * 0.12, t["fg"], t["bg0"])
        return draw_with_shadow(base, fg, t["shadow"])

    # 7. lame
    if affix_id == "lame":
        t = THEMES["neg1"]
        base = make_base_medallion("neg1")
        def fg(d):
            draw_horseshoe(d, CX, CY + W * 0.02, W * 0.24, W * 0.14, t["fg"], t["bg0"], cracked=True)
            # Diagonal warning slash
            d.line([(CX - W * 0.26, CY + W * 0.26), (CX + W * 0.26, CY - W * 0.26)], fill=t["accent"], width=int(W * 0.032))
        return draw_with_shadow(base, fg, t["shadow"])

    # 8. crippled
    if affix_id == "crippled":
        t = THEMES["neg2"]
        base = make_base_medallion("neg2")
        def fg(d):
            # Broken horseshoe split + heavy iron shackle ring
            draw_horseshoe(d, CX, CY - W * 0.04, W * 0.22, W * 0.13, t["fg"], t["bg0"], cracked=True)
            # Heavy X lock / chain bar across bottom
            d.line([(CX - W * 0.26, CY + W * 0.08), (CX + W * 0.26, CY + W * 0.32)], fill=t["accent"], width=int(W * 0.034))
            d.line([(CX + W * 0.26, CY + W * 0.08), (CX - W * 0.26, CY + W * 0.32)], fill=t["accent"], width=int(W * 0.034))
        return draw_with_shadow(base, fg, t["shadow"])

    # 9. big_heart
    if affix_id == "big_heart":
        t = THEMES["pos1"]
        base = make_base_medallion("pos1")
        def fg(d):
            # Concentric pulse rings around bold heart
            for r, col in [(0.34, t["rim_inner"]), (0.27, t["accent"])]:
                d.ellipse([CX - W * r, CY - W * r, CX + W * r, CY + W * r], outline=col, width=int(W * 0.016))
            d.polygon(heart_polygon(CX, CY + W * 0.01, W * 0.0135), fill=t["fg"])
            # Clean pulse line inside heart
            d.line(
                [(CX - W * 0.14, CY + W * 0.01), (CX - W * 0.06, CY + W * 0.01), (CX - W * 0.01, CY - W * 0.09), (CX + W * 0.05, CY + W * 0.09), (CX + W * 0.09, CY + W * 0.01), (CX + W * 0.15, CY + W * 0.01)],
                fill=t["bg1"],
                width=int(W * 0.022),
                joint="curve",
            )
        return draw_with_shadow(base, fg, t["shadow"])

    # 10. heart_condition
    if affix_id == "heart_condition":
        t = THEMES["neg1"]
        base = make_base_medallion("neg1")
        def fg(d):
            d.polygon(heart_polygon(CX, CY, W * 0.015), fill=t["fg"])
            # Jagged arrhythmia crack / flatline drop
            d.line(
                [(CX - W * 0.26, CY + W * 0.02), (CX - W * 0.09, CY + W * 0.02), (CX - W * 0.02, CY - W * 0.13), (CX + W * 0.06, CY + W * 0.16), (CX + W * 0.12, CY + W * 0.02), (CX + W * 0.28, CY + W * 0.02)],
                fill=t["bg0"],
                width=int(W * 0.032),
                joint="curve",
            )
            d.line(
                [(CX - W * 0.26, CY + W * 0.02), (CX - W * 0.09, CY + W * 0.02), (CX - W * 0.02, CY - W * 0.13), (CX + W * 0.06, CY + W * 0.16), (CX + W * 0.12, CY + W * 0.02), (CX + W * 0.28, CY + W * 0.02)],
                fill=t["accent"],
                width=int(W * 0.014),
                joint="curve",
            )
        return draw_with_shadow(base, fg, t["shadow"])

    # 11. nimble
    if affix_id == "nimble":
        t = THEMES["pos1"]
        base = make_base_medallion("pos1")
        def fg(d):
            # Twin crisp circular turning arrows
            r = W * 0.25
            bw = int(W * 0.038)
            d.arc([CX - r, CY - r, CX + r, CY + r], 210, 350, fill=t["fg"], width=bw)
            d.arc([CX - r, CY - r, CX + r, CY + r], 30, 170, fill=t["accent"], width=bw)
            # Arrowheads
            d.polygon([(CX + r * 0.96, CY - r * 0.02), (CX + r * 0.62, CY - r * 0.34), (CX + r * 1.18, CY - r * 0.38)], fill=t["fg"])
            d.polygon([(CX - r * 0.96, CY + r * 0.02), (CX - r * 0.62, CY + r * 0.34), (CX - r * 1.18, CY + r * 0.38)], fill=t["accent"])
            # Center pivot diamond
            cd = W * 0.075
            d.polygon([(CX, CY - cd), (CX + cd, CY), (CX, CY + cd), (CX - cd, CY)], fill=t["fg"])
        return draw_with_shadow(base, fg, t["shadow"])

    # 12. clumsy
    if affix_id == "clumsy":
        t = THEMES["neg1"]
        base = make_base_medallion("neg1")
        def fg(d):
            # Heavy iron weight/ball-and-chain dragging a sluggish turn arc downward
            # Iron ball
            br = W * 0.18
            bcx, bcy = CX, CY + W * 0.11
            d.ellipse([bcx - br, bcy - br, bcx + br, bcy + br], fill=t["fg"])
            # Subtle dark metallic highlight notch inside iron ball
            d.arc([bcx - br * 0.65, bcy - br * 0.65, bcx + br * 0.65, bcy + br * 0.65], 200, 290, fill=t["bg1"], width=int(W * 0.024))
            # Shackle collar + chain links up to downward arrow
            d.rectangle([bcx - W * 0.055, bcy - br - W * 0.045, bcx + W * 0.055, bcy - br + W * 0.02], fill=t["accent"])
            d.ellipse([bcx - W * 0.065, bcy - br - W * 0.155, bcx + W * 0.065, bcy - br - W * 0.035], outline=t["accent"], width=int(W * 0.026))
            draw_chevron(d, CX, CY - W * 0.29, W * 0.12, W * 0.055, False, t["accent"], int(W * 0.026))
        return draw_with_shadow(base, fg, t["shadow"])

    # 13. industrious
    if affix_id == "industrious":
        t = THEMES["pos1"]
        base = make_base_medallion("pos1")
        def fg(d):
            draw_bag_silhouette(d, CX - W * 0.04, CY + W * 0.04, W * 0.22, W * 0.22, t["fg"], t["accent"], t["bg0"])
            # Bright + badge on top right
            bx, by, br = CX + W * 0.22, CY - W * 0.20, W * 0.115
            d.ellipse([bx - br, by - br, bx + br, by + br], fill=t["accent"], outline=t["bg0"], width=int(W * 0.016))
            d.line([(bx - br * 0.55, by), (bx + br * 0.55, by)], fill=t["bg0"], width=int(W * 0.026))
            d.line([(bx, by - br * 0.55), (bx, by + br * 0.55)], fill=t["bg0"], width=int(W * 0.026))
        return draw_with_shadow(base, fg, t["shadow"])

    # 14. lazy
    if affix_id == "lazy":
        t = THEMES["neg1"]
        base = make_base_medallion("neg1")
        def fg(d):
            draw_bag_silhouette(d, CX - W * 0.05, CY + W * 0.08, W * 0.20, W * 0.19, t["fg"], t["accent"], t["bg0"])
            # Minus badge + Zzz lines at top right
            bx, by, br = CX + W * 0.21, CY - W * 0.18, W * 0.11
            d.ellipse([bx - br, by - br, bx + br, by + br], fill=t["accent"], outline=t["bg0"], width=int(W * 0.016))
            d.line([(bx - br * 0.52, by), (bx + br * 0.52, by)], fill=t["bg0"], width=int(W * 0.026))
            # Stylized Z mark
            zx, zy, zs = CX - W * 0.22, CY - W * 0.26, W * 0.075
            d.line([(zx - zs, zy - zs), (zx + zs, zy - zs), (zx - zs, zy + zs), (zx + zs, zy + zs)], fill=t["fg"], width=int(W * 0.020))
        return draw_with_shadow(base, fg, t["shadow"])

    # 15. battle_hardened (Special: crossed blades + veteran shield + living pulse spark)
    if affix_id == "battle_hardened":
        t = THEMES["special_war"]
        base = make_base_medallion("special_war", special=True)
        def fg(d):
            # Crossed veteran swords behind
            for sgn in (-1, 1):
                d.line(
                    [(CX - sgn * W * 0.29, CY + W * 0.28), (CX + sgn * W * 0.29, CY - W * 0.28)],
                    fill=t["rim"],
                    width=int(W * 0.034),
                )
                # Crossguard
                gx, gy = CX - sgn * W * 0.18, CY + W * 0.17
                d.line(
                    [(gx - W * 0.07, gy - sgn * W * 0.07), (gx + W * 0.07, gy + sgn * W * 0.07)],
                    fill=t["fg"],
                    width=int(W * 0.024),
                )
            draw_shield(d, CX, CY + W * 0.02, W * 0.21, W * 0.24, t["bg0"], t["rim"], int(W * 0.022))
            d.polygon(heart_polygon(CX, CY + W * 0.02, W * 0.0085), fill=t["accent"])
            # Crown spark above
            d.polygon(
                [(CX - W * 0.12, CY - W * 0.24), (CX - W * 0.15, CY - W * 0.34), (CX - W * 0.05, CY - W * 0.28), (CX, CY - W * 0.37), (CX + W * 0.05, CY - W * 0.28), (CX + W * 0.15, CY - W * 0.34), (CX + W * 0.12, CY - W * 0.24)],
                fill=t["rim"],
            )
        return draw_with_shadow(base, fg, t["shadow"])

    # 16. all_rounder (Special: radiant 6-pointed hexagram medallion)
    if affix_id == "all_rounder":
        t = THEMES["special_gold"]
        base = make_base_medallion("special_gold", special=True)
        def fg(d):
            # Outer hex ring
            r = W * 0.30
            hex_pts = [(CX + math.cos(math.radians(60 * i - 90)) * r, CY + math.sin(math.radians(60 * i - 90)) * r) for i in range(6)]
            d.line(hex_pts + [hex_pts[0]], fill=t["rim"], width=int(W * 0.018), joint="curve")
            # 6-point star burst
            star = []
            for i in range(12):
                ang = math.radians(30 * i - 90)
                rr = W * (0.31 if i % 2 == 0 else 0.13)
                star.append((CX + math.cos(ang) * rr, CY + math.sin(ang) * rr))
            d.polygon(star, fill=t["fg"], outline=t["accent"])
            # Inner golden gem
            cr = W * 0.085
            d.ellipse([CX - cr, CY - cr, CX + cr, CY + cr], fill=t["accent"], outline=t["bg0"], width=int(W * 0.016))
        return draw_with_shadow(base, fg, t["shadow"])

    # 17. pack_mule (Special: grand gilded expedition double-chest / pack)
    if affix_id == "pack_mule":
        t = THEMES["special_gold"]
        base = make_base_medallion("special_gold", special=True)
        def fg(d):
            # Twin stacked/gilded saddlebags
            draw_bag_silhouette(d, CX - W * 0.13, CY + W * 0.05, W * 0.17, W * 0.20, t["rim"], t["accent"], t["bg0"])
            draw_bag_silhouette(d, CX + W * 0.12, CY + W * 0.05, W * 0.17, W * 0.20, t["fg"], t["accent"], t["bg0"])
            # Golden arch bar linking twin packs + star crest
            d.line([(CX - W * 0.24, CY - W * 0.16), (CX + W * 0.24, CY - W * 0.16)], fill=t["rim"], width=int(W * 0.032))
            sd = W * 0.095
            d.polygon([(CX, CY - W * 0.26 - sd), (CX + sd * 0.7, CY - W * 0.26), (CX, CY - W * 0.26 + sd), (CX - sd * 0.7, CY - W * 0.26)], fill=t["fg"])
        return draw_with_shadow(base, fg, t["shadow"])

    # 18. warhorse (Special: armored destrier head + upright greatsword)
    if affix_id == "warhorse":
        t = THEMES["special_war"]
        base = make_base_medallion("special_war", special=True)
        def fg(d):
            # Vertical valor greatsword behind
            d.polygon(
                [(CX - W * 0.20, CY - W * 0.36), (CX - W * 0.15, CY - W * 0.28), (CX - W * 0.17, CY + W * 0.22), (CX - W * 0.23, CY + W * 0.22), (CX - W * 0.25, CY - W * 0.28)],
                fill=t["rim"],
            )
            d.rectangle([CX - W * 0.31, CY + W * 0.14, CX - W * 0.09, CY + W * 0.20], fill=t["fg"])
            d.rectangle([CX - W * 0.225, CY + W * 0.20, CX - W * 0.175, CY + W * 0.34], fill=t["accent"])
            # Bold armored horse head
            draw_horse_head(d, CX + W * 0.08, CY + W * 0.02, W * 0.48, t["fg"], t["accent"])
            # Armor brow plate accent
            d.line([(CX + W * 0.10, CY - W * 0.22), (CX + W * 0.30, CY - W * 0.04)], fill=t["rim"], width=int(W * 0.022))
        return draw_with_shadow(base, fg, t["shadow"])

    # 19. spirit_steed (Special: arcane rune ring + spirit steed head + star crystal)
    if affix_id == "spirit_steed":
        t = THEMES["special_arcane"]
        base = make_base_medallion("special_arcane", special=True)
        def fg(d):
            # Arcane circular rune ring
            r = W * 0.31
            d.ellipse([CX - r, CY - r, CX + r, CY + r], outline=t["accent"], width=int(W * 0.018))
            # 4-point arcane star on top-left
            sx, sy = CX - W * 0.20, CY - W * 0.20
            pts = []
            for i in range(8):
                ang = math.radians(45 * i)
                rr = W * (0.12 if i % 2 == 0 else 0.042)
                pts.append((sx + math.cos(ang) * rr, sy + math.sin(ang) * rr))
            d.polygon(pts, fill=t["rim"])
            # Ethereal horse head
            draw_horse_head(d, CX + W * 0.06, CY + W * 0.05, W * 0.46, t["fg"], t["accent"])
        return draw_with_shadow(base, fg, t["shadow"])

    # 20. tireless (Special: luminous infinity lemniscate + rising energy spark)
    if affix_id == "tireless":
        t = THEMES["special_stamina"]
        base = make_base_medallion("special_stamina", special=True)
        def fg(d):
            # Parametric lemniscate of Bernoulli
            pts = []
            n = 120
            a = W * 0.30
            for i in range(n + 1):
                th = 2.0 * math.pi * i / n
                denom = 1.0 + math.sin(th) ** 2
                x = CX + (a * math.cos(th)) / denom
                y = CY + W * 0.04 + (a * math.sin(th) * math.cos(th)) / denom
                pts.append((x, y))
            d.line(pts, fill=t["accent"], width=int(W * 0.066), joint="curve")
            d.line(pts, fill=t["fg"], width=int(W * 0.032), joint="curve")
            # Radiant energy flame / spark perched at top center
            d.polygon(
                [(CX, CY - W * 0.34), (CX + W * 0.08, CY - W * 0.18), (CX, CY - W * 0.11), (CX - W * 0.08, CY - W * 0.18)],
                fill=t["rim"],
            )
        return draw_with_shadow(base, fg, t["shadow"])

    raise ValueError(f"Unknown affix_id: {affix_id}")


AFFIXES = [
    ("very_strong", "非常强壮 +10%HP"),
    ("strong", "强壮 +5%HP"),
    ("frail", "瘦弱 -5%HP"),
    ("very_frail", "非常瘦弱 -10%HP"),
    ("fleet_footed", "健步如飞 +10%速"),
    ("swift", "迅捷 +5%速"),
    ("lame", "跛脚 -5%速"),
    ("crippled", "残疾 -10%速"),
    ("big_heart", "大心脏 +20%回体"),
    ("heart_condition", "心脏病 -20%回体"),
    ("nimble", "灵巧 +20%转向"),
    ("clumsy", "笨拙 -20%转向"),
    ("industrious", "勤劳 +2排包"),
    ("lazy", "懒惰 -2排包"),
    ("battle_hardened", "★身经百战"),
    ("all_rounder", "★多面手"),
    ("pack_mule", "★搬运工 +4排"),
    ("warhorse", "★战马"),
    ("spirit_steed", "★灵驹"),
    ("tireless", "★生生不息"),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    rendered = []
    for affix_id, label in AFFIXES:
        hi = make_icon(affix_id)
        out = hi.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        dst = OUT_DIR / f"{affix_id}.png"
        out.save(dst, "PNG")
        rendered.append((affix_id, label, out))

    # Build 5x4 contact sheet (with both large 144px and small 32px UI preview!)
    cols, rows = 5, 4
    cell_w, cell_h = 220, 220
    pad = 16
    sheet = Image.new("RGBA", (cols * cell_w + pad * 2, rows * cell_h + pad * 2), (14, 16, 20, 255))
    draw = ImageDraw.Draw(sheet)
    font = None
    for fpath in [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(fpath):
            font = ImageFont.truetype(fpath, 16)
            break
    if font is None:
        font = ImageFont.load_default()

    for idx, (affix_id, label, icon) in enumerate(rendered):
        c = idx % cols
        r = idx // cols
        x0 = pad + c * cell_w
        y0 = pad + r * cell_h
        draw.rounded_rectangle([x0 + 6, y0 + 6, x0 + cell_w - 6, y0 + cell_h - 6], radius=10, fill=(24, 27, 34, 255), outline=(60, 66, 78, 255), width=1)
        big = icon.resize((128, 128), Image.Resampling.LANCZOS)
        small = icon.resize((32, 32), Image.Resampling.LANCZOS)
        sheet.alpha_composite(big, (x0 + 22, y0 + 22))
        sheet.alpha_composite(small, (x0 + 162, y0 + 70))
        draw.text((x0 + 16, y0 + 166), label, fill=(232, 236, 242, 255), font=font)
        draw.text((x0 + 16, y0 + 190), affix_id, fill=(140, 148, 162, 255), font=font)

    sheet_path = REVIEW_DIR / "affix_icons_sheet.png"
    sheet.save(sheet_path, "PNG")
    print(f"Generated {len(rendered)} icons -> {OUT_DIR}")
    print(f"Contact sheet -> {sheet_path}")


if __name__ == "__main__":
    main()
