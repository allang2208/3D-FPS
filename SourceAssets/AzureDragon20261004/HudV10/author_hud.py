"""Bake the Azure Dragon HUD V10 layers from the approved concept upscales.

Inputs (local only, see README): Generated/empty_002.png and Generated/full_002.png are
Bailian image-edit upscales of the user's 2026-10-05 concept; they share pixel geometry.
Outputs: Export/*.png (display-space values, imported with sRGB off), Export/layout.json
and HudLayout.hlsl (constants shared by the UI material and preview).
"""
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parent
GEN = ROOT / 'Generated'
OUT = ROOT / 'Export'
OUT.mkdir(parents=True, exist_ok=True)
TEX_W, TEX_H = 512, 2048


def load(name):
    return np.asarray(Image.open(GEN / name).convert('RGB')).astype(np.float32) / 255.


E, F = load('empty_002.png'), load('full_002.png')
H, W = E.shape[:2]
if F.shape[:2] != (H, W):
    F = cv2.resize(F, (W, H), interpolation=cv2.INTER_AREA)
lum_e, lum_f = E.max(2), F.max(2)

# ---- measured layout in source pixels --------------------------------------------------
profile = cv2.GaussianBlur(lum_e[:, 500:625].mean(1).reshape(-1, 1), (1, 0), 3).ravel()
peaks, _ = find_peaks(profile, distance=60, prominence=.04)
body = lum_e[1000:2800]
edge_cols = np.where((body > .35).mean(0) > .5)[0]
left, right = int(edge_cols.min()), int(edge_cols.max())
center = .5 * (left + right)
apex = int(np.where(lum_e[:, int(center) - 25:int(center) + 25].max(1) > .3)[0].max())


def nearest(y):
    return int(peaks[np.argmin(np.abs(peaks - y))])


# The concept has a collar at the top/bottom and eight inner ticks: nine segments.
top_boundary, bottom_boundary = nearest(752), nearest(2921)
ticks = [nearest(y) for y in (985, 1218, 1469, 1721, 1955, 2198, 2434, 2672)]
levels = [apex] + ticks[::-1] + [top_boundary]  # level k reached at charge k/9
scale = TEX_H / H
x0 = center - .5 * TEX_W / scale


def tx(x):
    return (x - x0) * scale


def ty(y):
    return y * scale


# ---- concept palette ------------------------------------------------------------------
# Additive contribution sampled from the user's concept over its dark backdrop:
# empty glass ~ (33,68,75), filled interior ~ (38,164,169), highlights white-cyan.
RAMP_L = [0., .12, .30, .50, .70, .85, 1.]
# Empty glass reads pale silver-cyan (R/G ~ .55); the charged energy is saturated cyan (R/G ~ .3).
GLASS = np.array([[0, 0, 0], [.020, .050, .060], [.075, .190, .220], [.200, .410, .460],
                  [.420, .740, .800], [.700, .940, .980], [.950, 1., 1.]], np.float32)
ENERGY = np.array([[0, 0, 0], [.012, .060, .070], [.050, .220, .250], [.130, .480, .530],
                   [.320, .810, .860], [.620, .965, 1.0], [.940, 1., 1.]], np.float32)


def colorize(lum, gain, ramp):
    l = np.clip(lum * gain, 0, 1)
    return np.stack([np.interp(l, RAMP_L, ramp[:, c]) for c in range(3)], -1).astype(np.float32)


def interior_mean(img):
    return img[1000:2600, left + 25:right - 25].mean((0, 1))


empty = colorize(lum_e, .80, GLASS)
full = colorize(lum_f, 1., ENERGY)
# Calibrate the average interior contribution to the concept samples.
empty *= (np.array([.13, .27, .29]) / np.maximum(interior_mean(empty), 1e-3)).mean()
full *= (np.array([.15, .64, .66]) / np.maximum(interior_mean(full), 1e-3)).mean()
empty, full = np.clip(empty, 0, 1), np.clip(full, 0, 1)

# ---- masks -----------------------------------------------------------------------------
yy = np.arange(H)[:, None]
xx = np.arange(W)[None, :]
silhouette = cv2.GaussianBlur(lum_e, (0, 0), 3) > .10
column = silhouette & (yy > top_boundary - 120) & (xx > left - 30) & (xx < right + 30)
column = cv2.morphologyEx(column.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
# Fill the inside of the glass so the interior mask is solid between the edge lines.
filled = column.copy()
for y in range(H):
    xs = np.where(column[y])[0]
    if len(xs):
        filled[y, xs.min():xs.max() + 1] = 1
interior = cv2.erode(filled, np.ones((21, 21), np.uint8))
union = (cv2.GaussianBlur(lum_e, (0, 0), 3) > .12).astype(np.uint8) | filled
# The charged upscale painted a large S-vein through the column and dust around it. The
# concept's charged glass instead shows the same scale lattice glowing through an even cyan
# fill, so the column is rebuilt from the empty lattice; the charged upscale supplies the head.
soft_inner = cv2.GaussianBlur(cv2.erode(filled, np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 5)
lattice = colorize(lum_e, 1.10, ENERGY)
base_fill = soft_inner[..., None] * np.array([.02, .28, .31], np.float32)
column_full = 1. - (1. - lattice) * (1. - base_fill)
# Texture target sits below the concept's (38,164,169) sample: shader meniscus/streak layers add the rest.
column_full = column_full ** 1.25  # the concept keeps darker teal gaps between lit lattice lines
column_full *= (np.array([.10, .52, .55]) / np.maximum(interior_mean(column_full), 1e-3)).mean()
head_zone = cv2.GaussianBlur((yy < top_boundary - 40).astype(np.float32) * np.ones((1, W), np.float32), (0, 0), 12)
keep = cv2.GaussianBlur(cv2.dilate(union, np.ones((15, 15), np.uint8)).astype(np.float32), (0, 0), 6)
head_full = full * keep[..., None] + empty * (1 - keep[..., None])
full = np.clip(head_full * head_zone[..., None] + column_full * (1 - head_zone[..., None]), 0, 1)
dist = cv2.distanceTransform(1 - union, cv2.DIST_L2, 5)
glow = np.exp(-dist / 55.)
envelope = np.exp(-dist / 150.)


def fit(img, interp=cv2.INTER_AREA):
    """Crop the centred texture window and resize to the HUD texture."""
    pad = int(math.ceil(max(0., -x0))) + 4
    src = cv2.copyMakeBorder(img, 0, 0, pad, pad, cv2.BORDER_CONSTANT, value=0)
    ox = x0 + pad
    m = np.float32([[scale, 0, -ox * scale], [0, scale, 0]])
    return cv2.warpAffine(src, m, (TEX_W, TEX_H), flags=interp, borderMode=cv2.BORDER_CONSTANT)


def save(name, arr):
    arr = np.clip(arr, 0, 1)
    Image.fromarray((arr * 255 + .5).astype(np.uint8)).save(OUT / name)


# Pre-blur by the downscale ratio before resampling to keep thin edge lines.
def shrink(img):
    sigma = .5 / scale * .45
    return fit(cv2.GaussianBlur(img, (0, 0), sigma))


save('T_AzureDragonHudEmpty.png', shrink(empty))
save('T_AzureDragonHudFull.png', shrink(full))
mask = np.stack([filled.astype(np.float32), interior.astype(np.float32), glow, envelope], -1)
save('T_AzureDragonHudMask.png', shrink(mask))

# ---- rune glyph strip ------------------------------------------------------------------
rng = np.random.default_rng(20261005)
CELL, COUNT, SS = 64, 16, 4
strip = Image.new('L', (CELL * COUNT * SS, CELL * SS), 0)
draw = ImageDraw.Draw(strip)
width = int(5.5 * SS)
for g in range(COUNT):
    ox, s = g * CELL * SS, CELL * SS
    l, r, t, b = ox + .30 * s, ox + .70 * s, .16 * s, .84 * s
    mx = .5 * (l + r)
    kind = g % 4
    strokes = []
    if kind == 0:   # stem with branches (futhark-like)
        strokes.append(('line', mx, t, mx, b))
        for _ in range(rng.integers(1, 3)):
            yv = rng.uniform(t, .6 * (t + b))
            side = rng.choice([-1, 1])
            strokes.append(('line', mx, yv, mx + side * .2 * s, yv + rng.uniform(.1, .22) * s))
    elif kind == 1:  # angular chevron / zig
        pts = [(l, t + rng.uniform(0, .2) * s), (mx, b - rng.uniform(0, .2) * s), (r, t + rng.uniform(0, .2) * s)]
        strokes.append(('poly', pts))
        if rng.random() < .6:
            strokes.append(('dot', mx, t + .05 * s))
    elif kind == 2:  # arc with stem
        strokes.append(('arc', l, t + .1 * s, r, b - .2 * s, rng.integers(0, 4) * 90))
        strokes.append(('line', mx, .5 * (t + b), mx, b))
    else:            # crossed / loop
        strokes.append(('line', l, t, r, b))
        strokes.append(('line', r, t + rng.uniform(.1, .4) * s, l + rng.uniform(0, .15) * s, b))
        if rng.random() < .5:
            strokes.append(('ellipse', mx - .07 * s, t, mx + .07 * s, t + .14 * s))
    for st in strokes:
        if st[0] == 'line':
            draw.line(st[1:], fill=255, width=width)
            for px, py in (st[1:3], st[3:5]):
                draw.ellipse((px - width / 2, py - width / 2, px + width / 2, py + width / 2), fill=255)
        elif st[0] == 'poly':
            draw.line(st[1], fill=255, width=width, joint='curve')
        elif st[0] == 'dot':
            draw.ellipse((st[1] - width, st[2] - width, st[1] + width, st[2] + width), fill=255)
        elif st[0] == 'arc':
            draw.arc(st[1:5], st[5], st[5] + 220, fill=255, width=width)
        elif st[0] == 'ellipse':
            draw.ellipse(st[1:5], outline=255, width=width)
strip = strip.resize((CELL * COUNT, CELL), Image.LANCZOS)
strip.save(OUT / 'T_AzureDragonHudGlyphs.png')

# ---- tileable flame noise --------------------------------------------------------------
N = 256


def periodic(seed, cutoff, aniso=1.):
    r = np.random.default_rng(seed).standard_normal((N, N))
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.fftfreq(N)[None, :]
    k = np.sqrt((fx * aniso) ** 2 + fy ** 2)
    spec = np.fft.fft2(r) * np.exp(-(k / cutoff) ** 2)
    n = np.real(np.fft.ifft2(spec))
    return (n - n.min()) / (n.max() - n.min())


# Smooth, low-frequency fields: the concept flames are soft wisps, not grain.
fbm = .55 * periodic(1, .006) + .30 * periodic(2, .014) + .15 * periodic(3, .030)
strand_src = .75 * periodic(4, .010, .5) + .25 * periodic(5, .022, .5)
ridge = np.exp(-((strand_src - np.median(strand_src)) / .035) ** 2)
fbm2 = .6 * periodic(6, .008) + .4 * periodic(7, .018)
fine = .6 * periodic(8, .020) + .4 * periodic(9, .050)


def norm(a):
    return (a - a.min()) / (a.max() - a.min())


noise = np.stack([norm(fbm), norm(ridge), norm(fbm2), norm(fine)], -1)
save('T_AzureDragonHudNoise.png', noise)

# ---- layout ------------------------------------------------------------------------------
layout = dict(revision=10, source_size=[W, H], texture_size=[TEX_W, TEX_H], scale=scale, x0=x0,
              center=tx(center), half_width=.5 * (right - left) * scale,
              levels=[ty(v) for v in levels], cap_top=ty(top_boundary - 140), apex=ty(apex),
              ticks=[ty(v) for v in ticks], top_boundary=ty(top_boundary), bottom_boundary=ty(bottom_boundary),
              head_x=tx(float(np.mean(np.where(lum_e[:top_boundary - 140] > .3)[1]))), quad_top=-256.)
# Ribbon, shards measured on the 1/9 concept upscale (Generated/bar1_001.png, same frame).
layout['ribbon'] = dict(radius=160., pitch=384., thickness=27., top=430., turns=2.72)
layout['shards'] = [[352., 410., 18., 40., -.35], [54., 753., 17., 38., .42], [48., 1158., 18., 40., -.25],
                    [352., 1394., 17., 38., .35], [374., 905., 13., 30., -.15], [62., 1540., 14., 32., .30],
                    [62., 470., 12., 27., .5]]
(OUT / 'layout.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')
lines = ['// Generated by author_hud.py from the measured concept layout (texture pixels).',
         f'static const float2 HudSize = float2({TEX_W}.0, {TEX_H}.0);',
         f'static const float HudCenter = {layout["center"]:.2f};',
         f'static const float HudHalfWidth = {layout["half_width"]:.2f};',
         f'static const float HudCapTop = {layout["cap_top"]:.2f};',
         f'static const float HudTopBoundary = {layout["top_boundary"]:.2f};',
         f'static const float HudHeadX = {layout["head_x"]:.2f};',
         f'static const float HudQuadTop = {layout["quad_top"]:.1f};',
         'static const float HudLevels[10] = {' + ', '.join(f'{v:.2f}' for v in layout['levels']) + '};',
         'static const float HudTicks[8] = {' + ', '.join(f'{v:.2f}' for v in layout['ticks']) + '};',
         'static const float4 HudRibbon = float4({radius:.1f}, {pitch:.1f}, {thickness:.1f}, {top:.1f});'.format(**layout['ribbon']),
         f'static const float HudRibbonTurns = {layout["ribbon"]["turns"]:.3f};',
         'static const float4 HudShards[7] = {' + ', '.join(f'float4({s[0]:.1f}, {s[1]:.1f}, {s[2]:.1f}, {s[3]:.1f})' for s in layout['shards']) + '};',
         'static const float HudShardTilt[7] = {' + ', '.join(f'{s[4]:.2f}' for s in layout['shards']) + '};']
(ROOT / 'HudLayout.hlsl').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('AZURE_HUD_V10_BAKED', json.dumps({k: layout[k] for k in ('center', 'half_width', 'levels', 'apex')}))
