"""Arcane Circles V3 (2026-11-27) — 4K Supersampled Vector Generator -> 2048x2048 4-Channel Linear RGBA PNGs.

Generates museum-grade, razor-sharp 4-channel packed arcane textures for:
  1. ThunderLance  -> D:/FPS3D/FPSGAME/SourceAssets/ArcaneCirclesV3_20261127/T_ThunderLanceArcaneV3.png
  2. AbsoluteZero  -> D:/FPS3D/FPSGAME/SourceAssets/ArcaneCirclesV3_20261127/T_AbsoluteZeroArcaneV3.png

Channel Layout (Linear, sRGB=False, TC_BC7):
  R: Outer master bezels, 360/72/24 precision astrolabe vernier scale, cardinal/ordinal jewel medallions,
     and sacred geometric star lattice (12-pt lightning spear hexagram / 8-pt glacial snowflake crown).
  G: Independent counter-rotating calligraphic runic script band (24 / 32 genuinely distinct handcrafted
     Elder Futhark & astral-alchemical vector glyphs with chiseled stems, serifs, diacritics & ornate dividers).
  B: Inner clean-aperture micro-filigree, twin boundary hairlines, constellation pearl dots, gothic/crystal
     lace trim, and precision compass/reticle brackets.
  A: Tight stroke-hugging multi-scale Gaussian aura + vertex medallion glint cores (ZERO uniform band haze,
     strictly 0.0 inside clean central aperture: r < 0.565 ThunderLance, r < 0.485 AbsoluteZero).

Also writes high-res visual inspection sheets (full simulated Blue/Violet/Cyan shader render + 1:1 zoomed
quadrant crop + R/G/B/A channel breakdown) to:
  D:/FPS3D/FPSGAME/Work/ArcaneCirclesV3_20261127/preview_thunder.png
  D:/FPS3D/FPSGAME/Work/ArcaneCirclesV3_20261127/preview_absolute_zero.png
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

ROOT = Path(r"D:\FPS3D\FPSGAME")
SRC_OUT = ROOT / "SourceAssets" / "ArcaneCirclesV3_20261127"
WORK_OUT = ROOT / "Work" / "ArcaneCirclesV3_20261127"
SRC_OUT.mkdir(parents=True, exist_ok=True)
WORK_OUT.mkdir(parents=True, exist_ok=True)

SIZE_HI = 4096
SIZE_OUT = 2048
CX = (SIZE_HI - 1) * 0.5
CY = (SIZE_HI - 1) * 0.5
RAD = SIZE_HI * 0.5


# ---------------------------------------------------------------------------
# Low-level supersampled vector drawing helpers (operate on 4096x4096 float/L)
# ---------------------------------------------------------------------------

def polar(r: float, theta: float) -> Tuple[float, float]:
    """Convert normalized polar (r in [0..1], theta in radians) to 4K pixel coords."""
    return (CX + r * RAD * math.cos(theta), CY + r * RAD * math.sin(theta))


def draw_ring(draw: ImageDraw.ImageDraw, r: float, width_px: float, val: int = 255, steps: int = 720):
    """Draw a smooth circular ring at normalized radius r with stroke width in 4K pixels."""
    pts = [polar(r, 2.0 * math.pi * i / steps) for i in range(steps + 1)]
    w = max(1, int(round(width_px)))
    draw.line(pts, fill=val, width=w, joint="curve")


def draw_arc(draw: ImageDraw.ImageDraw, r: float, a0: float, a1: float, width_px: float, val: int = 255, steps: int = 64):
    pts = [polar(r, a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]
    draw.line(pts, fill=val, width=max(1, int(round(width_px))), joint="curve")


def draw_seg(draw: ImageDraw.ImageDraw, p0: Tuple[float, float], p1: Tuple[float, float], width_px: float, val: int = 255):
    w = max(1, int(round(width_px)))
    draw.line([p0, p1], fill=val, width=w)
    if w >= 4:
        rad = w * 0.45
        for px, py in (p0, p1):
            draw.ellipse([px - rad, py - rad, px + rad, py + rad], fill=val)


def draw_polyline(draw: ImageDraw.ImageDraw, pts: List[Tuple[float, float]], width_px: float, val: int = 255, closed: bool = False):
    if len(pts) < 2:
        return
    p = pts + [pts[0]] if closed else pts
    w = max(1, int(round(width_px)))
    draw.line(p, fill=val, width=w, joint="curve")
    if w >= 5:
        rad = w * 0.42
        for px, py in pts:
            draw.ellipse([px - rad, py - rad, px + rad, py + rad], fill=val)


def draw_dot(draw: ImageDraw.ImageDraw, pt: Tuple[float, float], rad_px: float, val: int = 255):
    x, y = pt
    draw.ellipse([x - rad_px, y - rad_px, x + rad_px, y + rad_px], fill=val)


def draw_diamond(draw: ImageDraw.ImageDraw, center_r: float, theta: float, dr: float, dt: float,
                 width_px: float = 0, fill_val: int | None = None, outline_val: int = 255):
    """Draw a diamond centered at polar (center_r, theta), radial half-size dr, tangential half-width dt (norm units)."""
    c = math.cos(theta)
    s = math.sin(theta)
    tx, ty = -s, c
    cx = CX + center_r * RAD * c
    cy = CY + center_r * RAD * s
    dr_px = dr * RAD
    dt_px = dt * RAD
    pts = [
        (cx + c * dr_px, cy + s * dr_px),
        (cx + tx * dt_px, cy + ty * dt_px),
        (cx - c * dr_px, cy - s * dr_px),
        (cx - tx * dt_px, cy - ty * dt_px),
    ]
    if fill_val is not None:
        draw.polygon(pts, fill=fill_val)
    if width_px > 0:
        draw_polyline(draw, pts, width_px, outline_val, closed=True)


def draw_clipped_chord(draw: ImageDraw.ImageDraw, p0: Tuple[float, float], p1: Tuple[float, float],
                       r_min: float, r_max: float, width_px: float, val: int = 255, samples: int = 240):
    """Draw a straight line segment clipped strictly to normalized annulus [r_min, r_max]."""
    x0, y0 = p0
    x1, y1 = p1
    run: List[Tuple[float, float]] = []
    for i in range(samples + 1):
        t = i / samples
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        rn = math.hypot(x - CX, y - CY) / RAD
        if r_min <= rn <= r_max:
            run.append((x, y))
        else:
            if len(run) >= 2:
                draw_polyline(draw, run, width_px, val)
            run = []
    if len(run) >= 2:
        draw_polyline(draw, run, width_px, val)


# ---------------------------------------------------------------------------
# 32 Distinct Calligraphic Arcane / Elder Futhark / Alchemical Vector Glyphs
# Each glyph is defined in local coords u in [-1, 1] (tangential), v in [-1, 1] (radial, +v outward).
# Returns (heavy_strokes, fine_strokes, dots) so every rune has authentic chiseled stroke hierarchy.
# ---------------------------------------------------------------------------

GLYPH_DEFS = [
    # 0: Fehu (wealth/energy flow)
    ([((-0.35, -0.95), (-0.35, 0.95))],
     [((-0.35, 0.15), (0.62, 0.88)), ((-0.35, -0.22), (0.55, 0.42)), ((-0.52, -0.95), (-0.18, -0.95)), ((-0.52, 0.95), (-0.18, 0.95))],
     [(0.58, -0.55)]),
    # 1: Uruz (primal force)
    ([((-0.48, -0.95), (-0.48, 0.95)), ((0.46, 0.35), (0.46, -0.95))],
     [((-0.48, 0.95), (0.46, 0.35)), ((-0.64, -0.95), (-0.30, -0.95)), ((0.30, -0.95), (0.62, -0.95)), ((-0.48, 0.05), (0.10, -0.25))],
     [(0.0, 0.18)]),
    # 2: Thurisaz (thorn / thunder gate)
    ([((-0.35, -0.95), (-0.35, 0.95))],
     [((-0.35, 0.48), (0.58, 0.0)), ((0.58, 0.0), (-0.35, -0.48)), ((-0.55, 0.95), (-0.15, 0.95)), ((-0.55, -0.95), (-0.15, -0.95)), ((-0.12, 0.24), (0.28, 0.0))],
     [(0.62, 0.58), (0.62, -0.58)]),
    # 3: Ansuz (aether voice)
    ([((-0.40, -0.95), (-0.40, 0.95))],
     [((-0.40, 0.88), (0.56, 0.28)), ((-0.40, 0.30), (0.56, -0.30)), ((-0.58, 0.95), (-0.22, 0.95)), ((-0.58, -0.95), (-0.22, -0.95))],
     [(0.38, -0.68)]),
    # 4: Raido (celestial chariot)
    ([((-0.42, -0.95), (-0.42, 0.95))],
     [((-0.42, 0.92), (0.52, 0.40)), ((0.52, 0.40), (-0.42, -0.05)), ((-0.12, -0.18), (0.56, -0.92)), ((-0.60, 0.95), (-0.24, 0.95)), ((-0.60, -0.95), (-0.24, -0.95))],
     [(0.48, 0.82)]),
    # 5: Kenaz (arcane torch)
    ([((0.46, 0.88), (-0.48, 0.0)), ((-0.48, 0.0), (0.46, -0.88))],
     [((0.56, 0.48), (0.04, 0.0)), ((0.04, 0.0), (0.56, -0.48)), ((0.30, 0.94), (0.62, 0.80)), ((0.30, -0.94), (0.62, -0.80))],
     [(-0.62, 0.0), (0.45, 0.0)]),
    # 6: Gebo (bound convergence)
    ([((-0.52, -0.88), (0.52, 0.88)), ((-0.52, 0.88), (0.52, -0.88))],
     [((-0.64, 0.88), (-0.36, 0.88)), ((0.36, 0.88), (0.64, 0.88)), ((-0.64, -0.88), (-0.36, -0.88)), ((0.36, -0.88), (0.64, -0.88))],
     [(0.0, 0.65), (0.0, -0.65)]),
    # 7: Wunjo (banner of glory)
    ([((-0.36, -0.95), (-0.36, 0.95))],
     [((-0.36, 0.92), (0.56, 0.42)), ((0.56, 0.42), (-0.36, -0.08)), ((-0.54, -0.95), (-0.18, -0.95)), ((-0.10, 0.60), (0.28, 0.40))],
     [(0.42, -0.58)]),
    # 8: Hagalaz (hail crystal)
    ([((-0.48, -0.92), (-0.48, 0.92)), ((0.48, -0.92), (0.48, 0.92))],
     [((-0.48, 0.56), (0.48, -0.56)), ((-0.48, 0.14), (0.48, -0.14)), ((-0.64, 0.92), (-0.32, 0.92)), ((0.32, -0.92), (0.64, -0.92))],
     [(0.0, 0.68), (0.0, -0.68)]),
    # 9: Nauthiz (binding spark)
    ([((0.0, -0.95), (0.0, 0.95))],
     [((-0.56, 0.44), (0.56, -0.34)), ((-0.26, 0.95), (0.26, 0.95)), ((-0.26, -0.95), (0.26, -0.95)), ((-0.38, -0.50), (0.38, -0.50))],
     [(-0.46, -0.24), (0.46, 0.36)]),
    # 10: Isa (glacial pillar)
    ([((0.0, -0.95), (0.0, 0.95))],
     [((-0.32, 0.92), (0.32, 0.92)), ((-0.32, -0.92), (0.32, -0.92)), ((-0.28, 0.0), (0.0, 0.32)), ((0.0, 0.32), (0.28, 0.0)), ((0.28, 0.0), (0.0, -0.32)), ((0.0, -0.32), (-0.28, 0.0))],
     [(-0.52, 0.0), (0.52, 0.0)]),
    # 11: Jera (orbital cycle)
    ([((-0.14, 0.90), (-0.54, 0.38)), ((-0.54, 0.38), (-0.08, -0.12)), ((0.14, -0.90), (0.54, -0.38)), ((0.54, -0.38), (0.08, 0.12))],
     [((-0.26, 0.94), (0.04, 0.86)), ((-0.04, -0.86), (0.26, -0.94))],
     [(0.0, 0.0), (0.45, 0.62), (-0.45, -0.62)]),
    # 12: Eihwaz (axis yew)
    ([((0.0, -0.92), (0.0, 0.92))],
     [((0.0, 0.92), (0.52, 0.36)), ((0.0, -0.92), (-0.52, -0.36)), ((-0.34, 0.24), (0.34, -0.24))],
     [(-0.44, 0.56), (0.44, -0.56)]),
    # 13: Perthro (arcane vessel)
    ([((-0.44, -0.92), (-0.44, 0.92))],
     [((-0.44, 0.92), (0.52, 0.92)), ((0.52, 0.92), (0.12, 0.38)), ((-0.44, -0.92), (0.52, -0.92)), ((0.52, -0.92), (0.12, -0.38)), ((-0.16, 0.0), (0.42, 0.0))],
     [(0.52, 0.0)]),
    # 14: Algiz (warding trident)
    ([((0.0, -0.95), (0.0, 0.95))],
     [((0.0, 0.08), (-0.58, 0.82)), ((0.0, 0.08), (0.58, 0.82)), ((-0.26, -0.95), (0.26, -0.95)), ((-0.36, -0.45), (0.36, -0.45))],
     [(0.0, 0.65), (-0.50, -0.18), (0.50, -0.18)]),
    # 15: Sowilo (lightning bolt)
    ([((-0.48, 0.92), (0.36, 0.14)), ((0.36, 0.14), (-0.36, -0.14)), ((-0.36, -0.14), (0.48, -0.92))],
     [((-0.62, 0.92), (-0.30, 0.92)), ((0.30, -0.92), (0.62, -0.92))],
     [(0.48, 0.66), (-0.48, -0.66)]),
    # 16: Tiwaz (sky spear)
    ([((0.0, -0.95), (0.0, 0.95))],
     [((0.0, 0.95), (-0.56, 0.22)), ((0.0, 0.95), (0.56, 0.22)), ((-0.28, -0.95), (0.28, -0.95)), ((-0.28, -0.25), (0.28, -0.25))],
     [(-0.46, -0.58), (0.46, -0.58)]),
    # 17: Berkano (twin crystal)
    ([((-0.42, -0.94), (-0.42, 0.94))],
     [((-0.42, 0.94), (0.48, 0.46)), ((0.48, 0.46), (-0.42, 0.0)), ((-0.42, 0.0), (0.48, -0.46)), ((0.48, -0.46), (-0.42, -0.94)), ((-0.60, 0.94), (-0.26, 0.94)), ((-0.60, -0.94), (-0.26, -0.94))],
     [(0.52, 0.0)]),
    # 18: Ehwaz (twin spires)
    ([((-0.48, -0.94), (-0.48, 0.94)), ((0.48, -0.94), (0.48, 0.94))],
     [((-0.48, 0.90), (0.0, 0.18)), ((0.0, 0.18), (0.48, 0.90)), ((-0.48, -0.35), (0.48, -0.35))],
     [(0.0, 0.70), (0.0, -0.70)]),
    # 19: Mannaz (arcane crown)
    ([((-0.48, -0.94), (-0.48, 0.94)), ((0.48, -0.94), (0.48, 0.94))],
     [((-0.48, 0.92), (0.48, 0.08)), ((0.48, 0.92), (-0.48, 0.08)), ((-0.48, -0.92), (-0.28, -0.92)), ((0.28, -0.92), (0.48, -0.92))],
     [(0.0, -0.45)]),
    # 20: Laguz (tidal wave)
    ([((-0.34, -0.94), (-0.34, 0.94))],
     [((-0.34, 0.94), (0.52, 0.24)), ((-0.34, 0.46), (0.28, -0.02)), ((-0.54, -0.94), (-0.14, -0.94))],
     [(0.38, -0.48), (0.38, -0.78)]),
    # 21: Ingwaz (lantern prism)
    ([((0.0, 0.88), (0.54, 0.0)), ((0.54, 0.0), (0.0, -0.88)), ((0.0, -0.88), (-0.54, 0.0)), ((-0.54, 0.0), (0.0, 0.88))],
     [((0.0, 0.46), (0.26, 0.0)), ((0.26, 0.0), (0.0, -0.46)), ((0.0, -0.46), (-0.26, 0.0)), ((-0.26, 0.0), (0.0, 0.46)), ((-0.24, 0.94), (0.24, 0.94)), ((-0.24, -0.94), (0.24, -0.94))],
     [(0.0, 0.0)]),
    # 22: Dagaz (hourglass dawn)
    ([((-0.52, -0.88), (-0.52, 0.88)), ((0.52, -0.88), (0.52, 0.88))],
     [((-0.52, 0.88), (0.52, -0.88)), ((-0.52, -0.88), (0.52, 0.88))],
     [(0.0, 0.64), (0.0, -0.64)]),
    # 23: Othala (citadel heritage)
    ([((0.0, 0.92), (0.52, 0.28)), ((0.52, 0.28), (-0.48, -0.92)), ((0.0, 0.92), (-0.52, 0.28)), ((-0.52, 0.28), (0.48, -0.92))],
     [((-0.22, 0.28), (0.22, 0.28))],
     [(0.0, -0.66)]),
    # 24: Astral Crescent Trident
    ([((0.0, -0.94), (0.0, 0.94))],
     [((-0.54, 0.56), (-0.32, 0.06)), ((-0.32, 0.06), (0.32, 0.06)), ((0.32, 0.06), (0.54, 0.56)), ((-0.36, -0.52), (0.36, -0.52))],
     [(-0.46, 0.78), (0.46, 0.78), (0.0, -0.94)]),
    # 25: Alchemical Storm Key
    ([((-0.44, 0.92), (0.44, 0.92)), ((0.0, 0.92), (0.0, -0.92))],
     [((-0.44, 0.92), (0.0, 0.28)), ((0.44, 0.92), (0.0, 0.28)), ((0.0, -0.25), (0.48, -0.25)), ((0.0, -0.64), (0.36, -0.64)), ((-0.26, -0.92), (0.26, -0.92))],
     [(-0.42, -0.45)]),
    # 26: Hex-Prism Conduit
    ([((-0.46, 0.46), (0.0, 0.92)), ((0.0, 0.92), (0.46, 0.46)), ((0.46, -0.46), (0.0, -0.92)), ((0.0, -0.92), (-0.46, -0.46))],
     [((-0.46, 0.46), (-0.46, -0.46)), ((0.46, 0.46), (0.46, -0.46)), ((-0.46, 0.0), (0.46, 0.0)), ((0.0, 0.92), (0.0, -0.92))],
     [(0.0, 0.45), (0.0, -0.45)]),
    # 27: Eclipse Caliper
    ([((-0.42, -0.92), (0.42, 0.92))],
     [((-0.54, 0.40), (0.0, 0.76)), ((0.0, 0.76), (0.54, 0.40)), ((-0.54, -0.40), (0.0, -0.76)), ((0.0, -0.76), (0.54, -0.40)), ((-0.36, 0.0), (0.36, 0.0))],
     [(-0.46, 0.80), (0.46, -0.80)]),
    # 28: Frost Compass Star
    ([((0.0, -0.94), (0.0, 0.94)), ((-0.56, 0.0), (0.56, 0.0))],
     [((-0.38, 0.56), (0.38, -0.56)), ((-0.38, -0.56), (0.38, 0.56)), ((-0.22, 0.72), (0.0, 0.94)), ((0.22, 0.72), (0.0, 0.94)), ((-0.22, -0.72), (0.0, -0.94)), ((0.22, -0.72), (0.0, -0.94))],
     [(0.0, 0.0)]),
    # 29: Twin Chevron Spire
    ([((-0.52, -0.10), (0.0, 0.92)), ((0.0, 0.92), (0.52, -0.10))],
     [((-0.44, -0.84), (0.0, 0.14)), ((0.0, 0.14), (0.44, -0.84)), ((0.0, 0.92), (0.0, -0.92))],
     [(-0.52, 0.56), (0.52, 0.56)]),
    # 30: Ouroboros Gate
    ([((-0.48, 0.76), (0.48, 0.76)), ((-0.48, -0.76), (0.48, -0.76))],
     [((-0.48, 0.76), (-0.48, -0.76)), ((0.48, 0.76), (0.48, -0.76)), ((-0.48, 0.0), (0.48, 0.0)), ((0.0, 0.96), (0.0, -0.96))],
     [(-0.24, 0.38), (0.24, -0.38)]),
    # 31: Glacial Chalice
    ([((-0.52, 0.88), (0.0, 0.04)), ((0.52, 0.88), (0.0, 0.04)), ((0.0, 0.04), (0.0, -0.94))],
     [((-0.38, -0.94), (0.38, -0.94)), ((-0.26, -0.52), (0.26, -0.52)), ((-0.36, 0.52), (0.36, 0.52))],
     [(0.0, 0.76), (-0.48, -0.28), (0.48, -0.28)]),
]


def draw_glyph(draw: ImageDraw.ImageDraw, glyph_idx: int, r_center: float, theta: float,
               half_r: float, half_t: float, heavy_w: float, fine_w: float, dot_r: float, val: int = 255):
    """Place calligraphic vector glyph cleanly oriented radially around the circle."""
    heavy, fine, dots = GLYPH_DEFS[glyph_idx % len(GLYPH_DEFS)]
    c = math.cos(theta)
    s = math.sin(theta)
    tx, ty = -s, c
    ox = CX + r_center * RAD * c
    oy = CY + r_center * RAD * s
    hr = half_r * RAD
    ht = half_t * RAD

    def to_px(uv: Tuple[float, float]) -> Tuple[float, float]:
        u, v = uv
        return (ox + tx * (u * ht) + c * (v * hr), oy + ty * (u * ht) + s * (v * hr))

    for a, b in heavy:
        draw_seg(draw, to_px(a), to_px(b), heavy_w, val)
    for a, b in fine:
        draw_seg(draw, to_px(a), to_px(b), fine_w, int(val * 0.92))
    for d in dots:
        draw_dot(draw, to_px(d), dot_r, val)


def draw_divider(draw: ImageDraw.ImageDraw, style: int, r_center: float, theta: float, half_r: float):
    """Ornate separator between glyphs (triple pearl, slender diamond, micro star)."""
    if style % 3 == 0:
        draw_diamond(draw, r_center, theta, half_r * 0.52, half_r * 0.24, width_px=3.5, outline_val=220)
        draw_dot(draw, polar(r_center, theta), 4.0, 255)
    elif style % 3 == 1:
        for dr in (-half_r * 0.52, 0.0, half_r * 0.52):
            draw_dot(draw, polar(r_center + dr, theta), 4.8 if dr == 0.0 else 3.4, 235)
    else:
        draw_seg(draw, polar(r_center - half_r * 0.58, theta), polar(r_center + half_r * 0.58, theta), 3.2, 210)
        draw_diamond(draw, r_center, theta, half_r * 0.26, half_r * 0.26, fill_val=240)


def draw_snowflake_dendrite(draw: ImageDraw.ImageDraw, r_base: float, r_tip: float, theta: float,
                            branch_scale: float = 1.0, val: int = 255):
    """Draw a delicate 60-degree symmetrical crystalline ice dendrite pointing radially outward."""
    c, s = math.cos(theta), math.sin(theta)
    tx, ty = -s, c
    p0 = polar(r_base, theta)
    p1 = polar(r_tip, theta)
    draw_seg(draw, p0, p1, 6.5 * branch_scale, val)
    span = (r_tip - r_base) * RAD
    for frac, blen_frac, bw in ((0.28, 0.42, 4.5), (0.54, 0.34, 4.0), (0.76, 0.22, 3.2)):
        bx = p0[0] + c * (span * frac)
        by = p0[1] + s * (span * frac)
        blen = span * blen_frac * branch_scale
        for side in (-1.0, 1.0):
            # 55-degree forward crystalline branch
            dx = c * 0.57 + tx * side * 0.82
            dy = s * 0.57 + ty * side * 0.82
            tip = (bx + dx * blen, by + dy * blen)
            draw_seg(draw, (bx, by), tip, bw * branch_scale, int(val * 0.94))
            # Secondary micro-barb on lower branch
            if frac < 0.6:
                mx = bx + dx * blen * 0.55
                my = by + dy * blen * 0.55
                sub = blen * 0.38
                draw_seg(draw, (mx, my), (mx + c * sub, my + s * sub), 2.8 * branch_scale, int(val * 0.85))
    # Hexagonal crystal node at root + diamond needle at tip
    draw_diamond(draw, r_base + (r_tip - r_base) * 0.14, theta, 0.015 * branch_scale, 0.010 * branch_scale,
                 width_px=3.5, outline_val=val)
    draw_dot(draw, p1, 5.2 * branch_scale, val)


def draw_medallion(draw: ImageDraw.ImageDraw, r_c: float, theta: float, med_r: float, mode: str):
    """Draw an ornate astrolabe rosette / jewel medallion at polar (r_c, theta)."""
    cx, cy = polar(r_c, theta)
    mr = med_r * RAD
    # Outer + inner fine rings of medallion
    for mult, w, v in ((1.0, 5.2, 255), (0.76, 3.0, 220)):
        rr = mr * mult
        pts = [(cx + rr * math.cos(2 * math.pi * i / 48), cy + rr * math.sin(2 * math.pi * i / 48)) for i in range(49)]
        draw.line(pts, fill=v, width=max(1, int(round(w))), joint="curve")
    if mode == "thunder":
        # 4-point electric compass star + inner bright core diamond
        for k in range(4):
            a = theta + k * math.pi * 0.5
            r_len = mr * (1.28 if k % 2 == 0 else 0.95)
            draw_seg(draw, (cx - math.cos(a) * r_len, cy - math.sin(a) * r_len),
                     (cx + math.cos(a) * r_len, cy + math.sin(a) * r_len), 4.0, 255)
        draw_diamond(draw, r_c, theta, med_r * 0.48, med_r * 0.34, fill_val=255)
    else:
        # 6-point hexagonal frost crystal rosette
        for k in range(6):
            a = theta + k * math.pi / 3.0
            draw_seg(draw, (cx, cy), (cx + math.cos(a) * mr * 0.96, cy + math.sin(a) * mr * 0.96), 3.6, 245)
        hex_pts = [(cx + mr * 0.48 * math.cos(theta + k * math.pi / 3.0),
                    cy + mr * 0.48 * math.sin(theta + k * math.pi / 3.0)) for k in range(6)]
        draw_polyline(draw, hex_pts, 3.8, 255, closed=True)
        draw_dot(draw, (cx, cy), mr * 0.22, 255)


# ---------------------------------------------------------------------------
# Radial masks & tight stroke-hugging glow synthesis
# ---------------------------------------------------------------------------

def build_radial_grid() -> np.ndarray:
    y, x = np.ogrid[:SIZE_HI, :SIZE_HI]
    return np.hypot(x - CX, y - CY).astype(np.float32) / float(RAD)


def make_strict_aperture_mask(r_grid: np.ndarray, r_clear: float, r_outer_max: float = 0.992) -> np.ndarray:
    inner = np.clip((r_grid - r_clear) / 0.005, 0.0, 1.0)
    inner = inner * inner * (3.0 - 2.0 * inner)
    outer = np.clip((r_outer_max - r_grid) / 0.012, 0.0, 1.0)
    outer = outer * outer * (3.0 - 2.0 * outer)
    return inner * outer


def synthesize_band_glow(r_f: np.ndarray, g_f: np.ndarray, b_f: np.ndarray,
                         jewel_img: Image.Image, r_grid: np.ndarray,
                         aperture_mask: np.ndarray, band_splits: Tuple[float, float]) -> np.ndarray:
    """Build band-isolated tight stroke-hugging glow so each counter-rotating layer carries its OWN glow!

    band_splits = (split_inner_rune, split_rune_outer):
      r < split_inner_rune   -> Channel B (inner filigree) glow only
      split_inner..split_out -> Channel G (calligraphic runes) glow only
      r > split_rune_outer   -> Channel R (outer master ring + star crown + medallions) glow only
    In UE5 HLSL, each layer's rotated Texture2DSample pulls its own co-rotating .a glow with ZERO ghosting!
    """
    s_in, s_out = band_splits
    jewels = np.asarray(jewel_img, dtype=np.float32) / 255.0

    def glow_of(ch: np.ndarray, jw: np.ndarray, sig1: float = 8.0, sig2: float = 22.0) -> np.ndarray:
        return gaussian_filter(ch, sigma=sig1) * 1.15 + gaussian_filter(ch, sigma=sig2) * 0.52 + gaussian_filter(jw, sigma=18.0) * 0.95 + jw * 0.65

    m_inner = np.clip((s_in - r_grid) / 0.006, 0.0, 1.0)
    m_outer = np.clip((r_grid - s_out) / 0.006, 0.0, 1.0)
    m_rune = np.clip((r_grid - s_in) / 0.006, 0.0, 1.0) * np.clip((s_out - r_grid) / 0.006, 0.0, 1.0)

    g_inner = glow_of(b_f, jewels * m_inner, sig1=7.5, sig2=19.0) * m_inner
    g_rune = glow_of(g_f, jewels * m_rune, sig1=8.0, sig2=20.0) * m_rune
    g_outer = glow_of(r_f, jewels * m_outer, sig1=9.0, sig2=25.0) * m_outer

    glow = np.clip(g_inner + g_rune + g_outer, 0.0, 1.0) * aperture_mask
    return glow


def pack_and_save(r_img: Image.Image, g_img: Image.Image, b_img: Image.Image,
                  jewel_img: Image.Image, r_grid: np.ndarray, r_clear: float,
                  band_splits: Tuple[float, float], out_path: Path):
    mask = make_strict_aperture_mask(r_grid, r_clear)
    r_f = (np.asarray(r_img, dtype=np.float32) / 255.0) * mask
    g_f = (np.asarray(g_img, dtype=np.float32) / 255.0) * mask
    b_f = (np.asarray(b_img, dtype=np.float32) / 255.0) * mask
    a_f = synthesize_band_glow(r_f, g_f, b_f, jewel_img, r_grid, mask, band_splits)

    # Hard-zero strictly inside r_clear - 0.001 so not even 1/255 leaks into center!
    hard_zero = r_grid < (r_clear - 0.001)
    r_f[hard_zero] = 0.0
    g_f[hard_zero] = 0.0
    b_f[hard_zero] = 0.0
    a_f[hard_zero] = 0.0

    # Downsample each channel cleanly 4096 -> 2048 via Lanczos
    def down(arr: np.ndarray) -> np.ndarray:
        im = Image.fromarray(np.clip(np.round(arr * 255.0), 0, 255).astype(np.uint8), mode="L")
        im = im.resize((SIZE_OUT, SIZE_OUT), Image.Resampling.LANCZOS)
        return np.asarray(im, dtype=np.uint8)

    rgba = np.stack([down(r_f), down(g_f), down(b_f), down(a_f)], axis=-1)
    # Re-enforce exact 0 in 2K inside aperture (eliminates any Lanczos ringing!)
    y2, x2 = np.ogrid[:SIZE_OUT, :SIZE_OUT]
    r2 = np.hypot(x2 - (SIZE_OUT - 1) * 0.5, y2 - (SIZE_OUT - 1) * 0.5) / (SIZE_OUT * 0.5)
    rgba[r2 < r_clear] = 0

    Image.fromarray(rgba, mode="RGBA").save(out_path, optimize=True)
    print(f"GENERATED {out_path} ({out_path.stat().st_size:,} bytes)", flush=True)
    return rgba


# ---------------------------------------------------------------------------
# 1. THUNDER LANCE ARCANE CIRCLE V3 (Clean Aperture r < 0.565)
# ---------------------------------------------------------------------------

def build_thunder_lance(r_grid: np.ndarray) -> np.ndarray:
    im_r = Image.new("L", (SIZE_HI, SIZE_HI), 0)
    im_g = Image.new("L", (SIZE_HI, SIZE_HI), 0)
    im_b = Image.new("L", (SIZE_HI, SIZE_HI), 0)
    im_j = Image.new("L", (SIZE_HI, SIZE_HI), 0)

    dr = ImageDraw.Draw(im_r)
    dg = ImageDraw.Draw(im_g)
    db = ImageDraw.Draw(im_b)
    dj = ImageDraw.Draw(im_j)

    # --- Channel R: Outer Master Architecture + Precision Astrolabe + 12-Pt Lightning Spear Hexagram ---
    # Primary double outer bezel + inner structural rail
    draw_ring(dr, 0.960, 12.0, 255)
    draw_ring(dr, 0.942, 4.5, 225)
    draw_ring(dr, 0.892, 6.5, 240)
    draw_ring(dr, 0.878, 3.0, 195)
    draw_ring(dr, 0.688, 7.5, 245)
    draw_ring(dr, 0.674, 3.2, 200)

    # 360 / 72 / 24 Astrolabe Vernier Degree Ticks inside [0.896, 0.938]
    for i in range(360):
        ang = 2.0 * math.pi * i / 360.0
        if i % 15 == 0:
            draw_seg(dr, polar(0.894, ang), polar(0.940, ang), 6.2, 255)
            draw_dot(dr, polar(0.951, ang), 5.0, 240)
        elif i % 5 == 0:
            draw_seg(dr, polar(0.902, ang), polar(0.938, ang), 4.0, 225)
        else:
            draw_seg(dr, polar(0.914, ang), polar(0.936, ang), 2.2, 165)

    # Interlaced Dual 6-Point Spearhead Hexagram: bold outside the rune band (r >= 0.862),
    # gossamer filigree chords across the rune corridor [0.688..0.862] so runes stay 100% crisp!
    for phase in (0.0, math.pi / 3.0):
        verts_outer = [polar(0.952, phase + k * 2.0 * math.pi / 3.0) for k in range(3)]
        verts_inner = [polar(0.922, phase + k * 2.0 * math.pi / 3.0) for k in range(3)]
        for k in range(3):
            draw_clipped_chord(dr, verts_outer[k], verts_outer[(k + 1) % 3], 0.862, 0.956, 8.6, 255)
            draw_clipped_chord(dr, verts_outer[k], verts_outer[(k + 1) % 3], 0.688, 0.864, 4.4, 155)
            draw_clipped_chord(dr, verts_inner[k], verts_inner[(k + 1) % 3], 0.862, 0.940, 3.8, 210)
            draw_clipped_chord(dr, verts_inner[k], verts_inner[(k + 1) % 3], 0.688, 0.864, 2.4, 115)

    # Secondary 30-deg offset lightning chevron lattice (bold outer spear tips + gossamer inner rails)
    for k in range(6):
        a_mid = (k + 0.5) * math.pi / 3.0
        a_l = a_mid - math.pi / 12.0
        a_r = a_mid + math.pi / 12.0
        p_tip = polar(0.938, a_mid)
        p_l = polar(0.688, a_l)
        p_r = polar(0.688, a_r)
        draw_clipped_chord(dr, p_l, p_tip, 0.862, 0.945, 5.8, 242)
        draw_clipped_chord(dr, p_r, p_tip, 0.862, 0.945, 5.8, 242)
        draw_clipped_chord(dr, p_l, p_tip, 0.688, 0.864, 3.2, 130)
        draw_clipped_chord(dr, p_r, p_tip, 0.688, 0.864, 3.2, 130)
        # Sharp outer lightning bolt crest at secondary peak
        draw_seg(dr, polar(0.942, a_mid), polar(0.976, a_mid), 5.0, 250)
        draw_diamond(dr, 0.916, a_mid, 0.020, 0.011, width_px=3.5, fill_val=195, outline_val=255)
        draw_dot(dj, polar(0.916, a_mid), 16.0, 215)

    # 6 Primary Cardinal Storm Medallions + Jagged Lightning Spear Finials at 0, 60, 120, 180, 240, 300 deg
    for k in range(6):
        ang = k * math.pi / 3.0
        draw_medallion(dr, 0.916, ang, 0.032, "thunder")
        draw_dot(dj, polar(0.916, ang), 26.0, 255)
        # Flanking lightning-arc horn wings hugging outer bezel (unmistakable storm silhouette!)
        draw_arc(dr, 0.974, ang - 0.125, ang + 0.125, 5.4, 245, steps=32)
        for side in (-1.0, 1.0):
            draw_seg(dr, polar(0.960, ang + side * 0.065), polar(0.985, ang + side * 0.035), 4.2, 240)
            draw_seg(dr, polar(0.985, ang + side * 0.035), polar(0.966, ang + side * 0.115), 3.4, 215)
        draw_diamond(dr, 0.974, ang, 0.018, 0.009, fill_val=255)
        # Inner anchor jewel at r = 0.688
        draw_diamond(dr, 0.688, ang, 0.020, 0.013, width_px=4.0, fill_val=160, outline_val=255)
        draw_dot(dj, polar(0.688, ang), 16.0, 220)

    # --- Channel G: 24 Distinct Calligraphic Arcane Runes + Ornate Scriptorium Rails ---
    draw_ring(dg, 0.858, 4.2, 235)
    draw_ring(dg, 0.848, 2.4, 185)
    draw_ring(dg, 0.718, 2.4, 185)
    draw_ring(dg, 0.708, 4.2, 235)

    num_runes = 24
    # Handpicked sequence of 24 visually distinct thunder/astral runes
    thunder_glyph_order = [15, 2, 16, 0, 4, 24, 5, 14, 1, 25, 3, 21, 12, 17, 6, 27, 7, 13, 19, 26, 22, 29, 23, 30]
    for i in range(num_runes):
        ang = 2.0 * math.pi * (i + 0.5) / num_runes
        draw_glyph(dg, thunder_glyph_order[i], r_center=0.783, theta=ang,
                   half_r=0.050, half_t=0.044, heavy_w=10.5, fine_w=5.8, dot_r=6.0, val=255)
        div_ang = 2.0 * math.pi * i / num_runes
        draw_divider(dg, i, r_center=0.783, theta=div_ang, half_r=0.046)
        # Subtle outer/inner script border diamonds above dividers
        draw_dot(dg, polar(0.853, div_ang), 4.2, 220)
        draw_dot(dg, polar(0.713, div_ang), 4.2, 220)

    # --- Channel B: Inner Clean-Aperture Micro-Filigree & Aim-Window Sight Brackets (r in [0.578, 0.668]) ---
    draw_ring(db, 0.660, 5.2, 245)
    draw_ring(db, 0.646, 2.6, 195)
    draw_ring(db, 0.594, 4.6, 250)
    draw_ring(db, 0.580, 2.5, 200)

    # Fine Gothic/Volt scalloped arch lace between 0.596 and 0.644 (48 pointed crystalline arches)
    n_arches = 48
    for i in range(n_arches):
        a0 = 2.0 * math.pi * i / n_arches
        am = 2.0 * math.pi * (i + 0.5) / n_arches
        a1 = 2.0 * math.pi * (i + 1.0) / n_arches
        p_l = polar(0.596, a0)
        p_peak = polar(0.644, am)
        p_r = polar(0.596, a1)
        draw_seg(db, p_l, p_peak, 3.2, 215)
        draw_seg(db, p_peak, p_r, 3.2, 215)
        draw_dot(db, polar(0.616, am), 3.6, 235)

    # 96 Constellation pearl dots hugging the crisp inner lip
    for i in range(96):
        ang = 2.0 * math.pi * i / 96.0
        if i % 8 != 0:
            draw_dot(db, polar(0.587, ang), 3.0 if i % 2 == 0 else 2.0, 215)

    # 8 Precision Sight Brackets framing the clean aiming window (4 cardinal + 4 ordinal)
    for k in range(8):
        ang = k * math.pi / 4.0
        is_card = (k % 2 == 0)
        span = 0.085 if is_card else 0.048
        # Crisp segmented aim bracket hugging r = 0.578..0.664
        draw_arc(db, 0.577, ang - span, ang + span, 6.0 if is_card else 4.2, 255, steps=24)
        draw_seg(db, polar(0.576, ang), polar(0.664, ang), 5.0 if is_card else 3.6, 255)
        if is_card:
            # Fine caliper cheek hooks at bracket ends
            for side in (-1.0, 1.0):
                draw_seg(db, polar(0.577, ang + side * span), polar(0.608, ang + side * span), 4.2, 240)
            draw_diamond(db, 0.620, ang, 0.022, 0.013, width_px=3.6, fill_val=200, outline_val=255)
            draw_dot(dj, polar(0.620, ang), 15.0, 230)
        else:
            draw_diamond(db, 0.620, ang, 0.014, 0.009, fill_val=240)

    return pack_and_save(im_r, im_g, im_b, im_j, r_grid, r_clear=0.565,
                         band_splits=(0.682, 0.870),
                         out_path=SRC_OUT / "T_ThunderLanceArcaneV3.png")


# ---------------------------------------------------------------------------
# 2. ABSOLUTE ZERO GROUND FROST SIGIL V3 (Clean Aperture r < 0.485)
# ---------------------------------------------------------------------------

def build_absolute_zero(r_grid: np.ndarray) -> np.ndarray:
    im_r = Image.new("L", (SIZE_HI, SIZE_HI), 0)
    im_g = Image.new("L", (SIZE_HI, SIZE_HI), 0)
    im_b = Image.new("L", (SIZE_HI, SIZE_HI), 0)
    im_j = Image.new("L", (SIZE_HI, SIZE_HI), 0)

    dr = ImageDraw.Draw(im_r)
    dg = ImageDraw.Draw(im_g)
    db = ImageDraw.Draw(im_b)
    dj = ImageDraw.Draw(im_j)

    # --- Channel R: Outer Glacial Crown + 8-Pt Interlaced Octagram + Branching Snowflake Dendrites ---
    draw_ring(dr, 0.964, 12.5, 255)
    draw_ring(dr, 0.946, 4.5, 225)
    draw_ring(dr, 0.890, 6.8, 242)
    draw_ring(dr, 0.876, 3.0, 195)
    draw_ring(dr, 0.624, 7.2, 242)
    draw_ring(dr, 0.610, 3.2, 195)

    # 360 / 72 / 16 Crystalline Compass Vernier Scale in [0.894, 0.942]
    for i in range(360):
        ang = 2.0 * math.pi * i / 360.0
        if i % 15 == 0:
            draw_seg(dr, polar(0.892, ang), polar(0.944, ang), 5.8, 255)
        elif i % 5 == 0:
            draw_seg(dr, polar(0.902, ang), polar(0.940, ang), 3.8, 220)
        else:
            draw_seg(dr, polar(0.918, ang), polar(0.940, ang), 2.1, 160)

    # Grand 8-Point Interlaced Glacial Star Crown: razor-bold in outer crown (r >= 0.860),
    # gossamer crystalline filigree across the rune corridor [0.625..0.860] so all 32 frost runes pop!
    for phase in (0.0, math.pi / 4.0):
        v_out = [polar(0.958, phase + k * math.pi / 2.0) for k in range(4)]
        v_in = [polar(0.924, phase + k * math.pi / 2.0) for k in range(4)]
        for k in range(4):
            draw_clipped_chord(dr, v_out[k], v_out[(k + 1) % 4], 0.860, 0.960, 8.6, 255)
            draw_clipped_chord(dr, v_out[k], v_out[(k + 1) % 4], 0.624, 0.862, 4.4, 150)
            draw_clipped_chord(dr, v_in[k], v_in[(k + 1) % 4], 0.860, 0.938, 3.8, 210)
            draw_clipped_chord(dr, v_in[k], v_in[(k + 1) % 4], 0.624, 0.862, 2.4, 110)

    # Secondary 8-Point Faceted Frost Spire Crown (crisp polygonal diamond facets + branching dendrites)
    for k in range(8):
        a_mid = (k + 0.5) * math.pi / 4.0
        a_l = a_mid - math.pi / 16.0
        a_r = a_mid + math.pi / 16.0
        draw_clipped_chord(dr, polar(0.624, a_l), polar(0.920, a_mid), 0.860, 0.925, 5.2, 240)
        draw_clipped_chord(dr, polar(0.624, a_r), polar(0.920, a_mid), 0.860, 0.925, 5.2, 240)
        draw_clipped_chord(dr, polar(0.624, a_l), polar(0.920, a_mid), 0.624, 0.862, 2.8, 120)
        draw_clipped_chord(dr, polar(0.624, a_r), polar(0.920, a_mid), 0.624, 0.862, 2.8, 120)
        # Delicate branching frost dendrite protruding slightly past bezel for glacial silhouette
        draw_snowflake_dendrite(dr, 0.862, 0.976, a_mid, branch_scale=0.78, val=242)
        draw_dot(dj, polar(0.916, a_mid), 16.0, 210)

    # 8 Major Cardinal/Ordinal Glacial Snowflake Dendrites + Hexagonal Rosette Medallions
    for k in range(8):
        ang = k * math.pi / 4.0
        draw_medallion(dr, 0.896, ang, 0.032, "frost")
        draw_snowflake_dendrite(dr, 0.858, 0.986, ang, branch_scale=1.10, val=255)
        draw_dot(dj, polar(0.896, ang), 26.0, 255)
        # Inner crystalline anchor facet on structural rail
        draw_diamond(dr, 0.624, ang, 0.024, 0.014, width_px=4.0, fill_val=175, outline_val=255)
        draw_dot(dj, polar(0.624, ang), 16.0, 225)

    # --- Channel G: 32 Distinct Calligraphic Frost/Astral Runes in [0.642, 0.854] ---
    draw_ring(dg, 0.854, 4.4, 238)
    draw_ring(dg, 0.844, 2.4, 185)
    draw_ring(dg, 0.654, 2.4, 185)
    draw_ring(dg, 0.644, 4.4, 238)

    num_runes = 32
    # All 32 bespoke distinct glyphs arranged around the grand 5.2m ground circle!
    frost_glyph_order = [
        10, 8, 28, 31, 14, 21, 18, 12,
        26, 11, 9, 20, 24, 6, 16, 30,
        29, 3, 27, 13, 19, 22, 23, 17,
        25, 5, 7, 15, 4, 2, 1, 0,
    ]
    for i in range(num_runes):
        ang = 2.0 * math.pi * (i + 0.5) / num_runes
        draw_glyph(dg, frost_glyph_order[i], r_center=0.749, theta=ang,
                   half_r=0.064, half_t=0.041, heavy_w=10.2, fine_w=5.6, dot_r=5.8, val=255)
        div_ang = 2.0 * math.pi * i / num_runes
        draw_divider(dg, i, r_center=0.749, theta=div_ang, half_r=0.056)
        draw_dot(dg, polar(0.849, div_ang), 4.0, 220)
        draw_dot(dg, polar(0.649, div_ang), 4.0, 220)

    # --- Channel B: Inner Clean-Center Frost Lotus Lace & Synergy Braid Rim (r in [0.498, 0.608]) ---
    draw_ring(db, 0.602, 5.4, 245)
    draw_ring(db, 0.588, 2.6, 195)
    draw_ring(db, 0.514, 5.2, 252)
    draw_ring(db, 0.500, 2.6, 205)

    # Double-braided crystalline crystal-lotus lattice between 0.516 and 0.586 (32 interlaced frost petals)
    n_petals = 32
    for i in range(n_petals):
        a0 = 2.0 * math.pi * i / n_petals
        am = 2.0 * math.pi * (i + 0.5) / n_petals
        a1 = 2.0 * math.pi * (i + 1.0) / n_petals
        # Primary crystal lotus chevron
        draw_seg(db, polar(0.516, a0), polar(0.586, am), 3.8, 235)
        draw_seg(db, polar(0.586, am), polar(0.516, a1), 3.8, 235)
        # Inverted counter-lace chevron (creates diamond frost mesh!)
        draw_seg(db, polar(0.586, a0), polar(0.516, am), 2.8, 190)
        draw_seg(db, polar(0.516, am), polar(0.586, a1), 2.8, 190)
        draw_dot(db, polar(0.551, am), 4.0, 245)

    # 64 Constellation frost pearls along inner clean lip
    for i in range(64):
        ang = 2.0 * math.pi * i / 64.0
        draw_dot(db, polar(0.507, ang), 3.2 if i % 2 == 0 else 2.2, 220)

    # 8 Cardinal/Ordinal Compass Crystal Needles framing the caster's clean floor space
    for k in range(8):
        ang = k * math.pi / 4.0
        span = 0.095 if k % 2 == 0 else 0.055
        draw_arc(db, 0.498, ang - span, ang + span, 5.8 if k % 2 == 0 else 4.0, 255, steps=24)
        draw_diamond(db, 0.551, ang, 0.032 if k % 2 == 0 else 0.022, 0.016 if k % 2 == 0 else 0.011,
                     width_px=3.8, fill_val=215, outline_val=255)
        draw_dot(dj, polar(0.551, ang), 14.0, 220)

    return pack_and_save(im_r, im_g, im_b, im_j, r_grid, r_clear=0.485,
                         band_splits=(0.628, 0.864),
                         out_path=SRC_OUT / "T_AbsoluteZeroArcaneV3.png")


# ---------------------------------------------------------------------------
# Visual Review Render (simulates Blue/Violet/Cyan white-hot-core shader!)
# ---------------------------------------------------------------------------

def render_preview_sheet(rgba: np.ndarray, title: str, r_clear: float, out_path: Path):
    """Render a 2048x1200 visual inspection sheet: full shader preview + 1:1 crop + R/G/B/A breakdown."""
    h, w, _ = rgba.shape
    arr = rgba.astype(np.float32) / 255.0
    R, G, B, A = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]

    # Simulate the Blue / Violet / Cyan iridescent color walk across angle & layer
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    dx = (xx - (w - 1) * 0.5) / (w * 0.5)
    dy = (yy - (h - 1) * 0.5) / (h * 0.5)
    ang = np.arctan2(dy, dx)

    c_blue = np.array([0.16, 0.54, 1.00], dtype=np.float32)
    c_violet = np.array([0.68, 0.24, 1.00], dtype=np.float32)
    c_cyan = np.array([0.08, 0.95, 1.00], dtype=np.float32)

    # Smooth spatial blend of Blue -> Violet -> Cyan around ring so all 3 hues are visible in review
    t = (np.sin(ang * 1.5 + 0.4) * 0.5 + 0.5)[..., None]
    t2 = (np.cos(ang * 2.0 - 0.6) * 0.5 + 0.5)[..., None]
    col_outer = c_blue * (1.0 - t) + c_violet * t
    col_rune = c_cyan * (1.0 - t2) + c_blue * t2
    col_inner = c_violet * (1.0 - t) + c_cyan * t

    core = np.maximum(np.maximum(R, G), B)[..., None]
    w_sum = np.maximum(1e-4, R + G + B)[..., None]
    chroma = (col_outer * R[..., None] + col_rune * G[..., None] + col_inner * B[..., None]) / w_sum
    # White-hot incandescent stroke core + colored tight stroke aura
    glow_rgb = (col_outer * 0.55 + col_rune * 0.45) * (A[..., None] * 0.95)
    core_rgb = (chroma * 0.55 + np.array([0.95, 0.98, 1.0], dtype=np.float32) * 0.45) * (core ** 0.90) * 1.35

    # Dark twilight slate background (reveals subtle alpha artifacts AND crispness)
    bg = np.zeros((h, w, 3), dtype=np.float32)
    bg[..., 0] = 0.035
    bg[..., 1] = 0.045
    bg[..., 2] = 0.075
    comp = bg + glow_rgb + core_rgb
    # Filmic ACES-like soft shoulder so white-hot cores read naturally without ugly clipping
    comp = comp / (1.0 + comp * 0.42)
    comp = np.power(np.clip(comp, 0.0, 1.0), 1.0 / 1.15)
    sim_img = Image.fromarray(np.clip(comp * 255.0, 0, 255).astype(np.uint8), mode="RGB")

    # Assemble 2048x1200 inspection sheet
    sheet = Image.new("RGB", (2048, 1200), (12, 15, 22))
    draw = ImageDraw.Draw(sheet)

    # Left panel: 1120x1120 full preview
    full_vis = sim_img.resize((1120, 1120), Image.Resampling.LANCZOS)
    # Draw thin dashed red clean-aperture reference circle & center crosshair on the preview ONLY
    fd = ImageDraw.Draw(full_vis)
    fc = 560.0
    r_px = r_clear * 560.0
    for i in range(0, 72, 2):
        a0 = 2.0 * math.pi * i / 72.0
        a1 = 2.0 * math.pi * (i + 1) / 72.0
        fd.line([(fc + r_px * math.cos(a0), fc + r_px * math.sin(a0)),
                 (fc + r_px * math.cos(a1), fc + r_px * math.sin(a1))], fill=(255, 85, 85), width=2)
    fd.line([(fc - 18, fc), (fc + 18, fc)], fill=(255, 110, 110), width=2)
    fd.line([(fc, fc - 18), (fc, fc + 18)], fill=(255, 110, 110), width=2)
    sheet.paste(full_vis, (24, 56))
    draw.text((28, 18), f"{title} — Full Shader Preview (Red dashed = strict 0-opacity clean center r<{r_clear:.3f})", fill=(220, 235, 255))

    # Right-top panel: 1:1 TRUE PIXEL 560x560 crop of top-right quadrant (exact 2K native sharpness!)
    crop_box = (1180, 120, 1740, 680)
    crop_1to1 = sim_img.crop(crop_box)
    sheet.paste(crop_1to1, (1180, 56))
    draw.rectangle([1179, 55, 1741, 617], outline=(90, 150, 220), width=2)
    draw.text((1182, 24), "1:1 Native 2K Detail Crop (Outer Bezel + Vernier + Runes + Inner Filigree)", fill=(220, 235, 255))

    # Right-bottom panel: 2x2 Channel Breakdown (R, G, B, A) each 268x268
    ch_names = [("R: Outer Geometry", 0), ("G: Calligraphic Runes", 1), ("B: Inner Filigree", 2), ("A: Tight Glow & Glints", 3)]
    for idx, (label, ci) in enumerate(ch_names):
        gx = 1180 + (idx % 2) * 284
        gy = 648 + (idx // 2) * 276
        ch_im = Image.fromarray(rgba[..., ci], mode="L").resize((250, 250), Image.Resampling.LANCZOS).convert("RGB")
        sheet.paste(ch_im, (gx, gy + 18))
        draw.rectangle([gx - 1, gy + 17, gx + 251, gy + 269], outline=(70, 95, 130), width=1)
        draw.text((gx, gy), label, fill=(180, 210, 240))

    sheet.save(out_path, optimize=True)
    print(f"PREVIEW   {out_path} ({out_path.stat().st_size:,} bytes)", flush=True)


def main():
    r_grid = build_radial_grid()
    rgba_thunder = build_thunder_lance(r_grid)
    rgba_az = build_absolute_zero(r_grid)

    render_preview_sheet(rgba_thunder, "T_ThunderLanceArcaneV3 (2048x2048)", 0.565, WORK_OUT / "preview_thunder.png")
    render_preview_sheet(rgba_az, "T_AbsoluteZeroArcaneV3 (2048x2048)", 0.485, WORK_OUT / "preview_absolute_zero.png")
    print("ARCANE_V3_TEXTURES_OK", flush=True)


if __name__ == "__main__":
    main()
