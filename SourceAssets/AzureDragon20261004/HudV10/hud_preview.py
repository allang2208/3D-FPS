"""Offline twin of AzureDragonHud.hlsl for authoring the HUD layers (not a UE render).

Mirrors the UI material statement by statement in display space (Slate NoGamma, additive).
Writes comparison sheets to %TEMP%/azure_v10 so the concept can be compared at 1/9, 5/9, 9/9.
"""
import json
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'Export'
LAYOUT = json.loads((EXP / 'layout.json').read_text(encoding='utf-8'))


def tex(name, channels=3):
    a = np.asarray(Image.open(EXP / name)).astype(np.float32) / 255.
    return a if a.ndim == 3 else a[..., None]


TE, TF = tex('T_AzureDragonHudEmpty.png'), tex('T_AzureDragonHudFull.png')
TM, TN, TG = tex('T_AzureDragonHudMask.png'), tex('T_AzureDragonHudNoise.png'), tex('T_AzureDragonHudGlyphs.png')
SIZE = np.array(LAYOUT['texture_size'], np.float32)
CENTER, TOPB = LAYOUT['center'], LAYOUT['top_boundary']
LEVELS = np.array(LAYOUT['levels'], np.float32)
RIB = LAYOUT['ribbon']
SHARDS = LAYOUT['shards']
DEBUG = os.environ.get('HUD_DEBUG', '')
HEADX = LAYOUT['head_x']
QUAD_TOP = LAYOUT['quad_top']


def sample(t, u, v, wrap=False):
    h, w = t.shape[:2]
    mx, my = (u * w - .5).astype(np.float32), (v * h - .5).astype(np.float32)
    if wrap:
        mx, my = np.mod(mx, w), np.mod(my, h)
        out = cv2.remap(t, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    else:
        out = cv2.remap(t, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return out if out.ndim == 3 else out[..., None]


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def sat(x):
    return np.clip(x, 0, 1)


def render(fill, age, pulse=0., burst=0., reveal=1., res=1.):
    """Quad covers texture x [0,512], y [QUAD_TOP, 2048]: headroom for the crown flames."""
    w, h = int(SIZE[0]), int(SIZE[1])
    n_w, n_h = int(w * res), int((h - QUAD_TOP) * res)
    px, py = np.meshgrid((np.arange(n_w, dtype=np.float32) + .5) / res,
                         (np.arange(n_h, dtype=np.float32) + .5) / res + QUAD_TOP)
    u, v = px / w, py / h
    f9 = min(max(fill, 0.), 1.) * 9.
    k = int(min(math.floor(f9), 8))
    men_y = LEVELS[k] + (LEVELS[k + 1] - LEVELS[k]) * (f9 - k)
    charged = 1. if fill > .001 else 0.
    zone = smoothstep(TOPB - 16., TOPB + 16., py)
    cap = smoothstep(8.4 / 9., 1., fill)
    wave = 1.6 * np.sin(px * .09 + age * 3.1) + 1.0 * np.sin(px * .21 - age * 4.7)
    below = smoothstep(men_y - 1.5, men_y + 1.5, py + wave) * charged
    mix = zone * below + (1 - zone) * (.20 + .45 * cap)
    m = sample(TM, u, v)
    sil, inner, glow, env = m[..., 0], m[..., 1], m[..., 2], m[..., 3]
    col = sample(TE, u, v) * (1 - mix[..., None]) + sample(TF, u, v) * (1 + .35 * pulse + .4 * burst) * mix[..., None]
    base_lum = col.max(2)

    # Energy streaks flowing up inside the filled glass.
    n1 = sample(TN, px / 520. + .13 * math.sin(age * .3), py / 1100. + age * .06, True)[..., 1]
    n2 = sample(TN, px / 330. + .37, py / 700. + age * .045, True)[..., 1]
    streak = (n1 * n2) ** 1.5 * inner * below * zone * .30
    col += streak[..., None] * np.array([.15, .85, 1.])

    # Meniscus line and the brighter liquid just below it.
    d = py + wave - men_y
    men = (np.exp(-d * d / (2 * 2.2 * 2.2)) * .95 + np.exp(-np.maximum(d, 0) / 14.) * (d > 0) * .15) * inner * zone * charged
    col += men[..., None] * np.array([.75, 1., 1.])

    # Inner flames above the surface.
    hgt = men_y - py
    flen = 170. + 90. * fill
    nf = .65 * sample(TN, px / 80., py / 320. + age * .30, True)[..., 0] + .35 * sample(TN, px / 45. + .5, py / 160. + age * .45, True)[..., 3]
    rel = hgt / flen
    edge0 = .44 + .24 * rel
    tongue = (smoothstep(edge0, edge0 + .14, nf) * .70 + np.exp(-((nf - edge0) / .022) ** 2) * .65) * (hgt > 0) * (rel < 1)
    inner_fire = tongue * np.sqrt(sat(1. - rel)) * inner * zone * charged * (.9 + .5 * burst)
    col += inner_fire[..., None] * np.array([.25, .95, 1.])

    # Outer flames: soft tongues with bright rims around the charged vessel, crowning the head when full.
    reach = 110. + 330. * fill + 150. * burst
    vfade = sat(1. - (men_y - py) / reach)
    amount = min(1., .45 + .55 * fill + .6 * burst)
    wx = sample(TN, px / 700. + .4, py / 1000. + age * .05, True)
    qx, qy = px / 300. + (wx[..., 2] - .5) * .45, py / 820. + age * .17 + (wx[..., 0] - .5) * .35
    n = sample(TN, qx, qy, True)[..., 0]
    n2 = sample(TN, qx * 2.3 + .17, qy * 2.0 + age * .05, True)[..., 3]
    plume = cap * np.exp(-((px - HEADX) / 80.) ** 2) * smoothstep(QUAD_TOP + 10., 80., py) * smoothstep(TOPB + 40., TOPB - 160., py)
    shape = ((glow ** .9 * .70 + env ** 3. * .25) * (1. - .55 * (1. - zone)) + plume * 1.1) * vfade * charged
    dens = shape * amount * (n * .75 + n2 * .45) ** 1.5 * 2.6
    fx_, fy_ = qx * 1.4 + (n - .5) * .5, qy * 1.1 + .31
    strands = sample(TN, fx_, fy_, True)[..., 1] * smoothstep(.05, .30, dens)
    tongue = smoothstep(.30, .85, dens) * .42 + (smoothstep(.10, .26, dens) - smoothstep(.26, .50, dens)) * .55
    # Keep the dragon readable: flames lick around the head silhouette, not over it.
    fire = (tongue + strands * .70) * (1. - .85 * inner) * (1. - .65 * (1. - zone) * smoothstep(.80, 1., glow))
    if DEBUG == 'fire':
        return sat(fire[..., None] * np.array([.30, .90, 1.]))
    top = smoothstep(TOPB - 250., TOPB - 420., py) * cap
    fire_col = np.array([.18, .88, 1.])[None, None] * (1 - top[..., None] * .6) + np.array([.28, .45, 1.])[None, None] * top[..., None] * .6
    col += fire[..., None] * fire_col * 1.1

    # Halo.
    col += (glow * (.04 + .08 * fill + .2 * pulse + .3 * burst))[..., None] * np.array([.20, .75, .85])

    # Helical rune ribbon (rotation == travel along the band).
    s = (CENTER - px) / RIB['radius']
    ok = np.abs(s) < .999
    s_c = np.clip(s, -.999, .999)
    phi = age * .45
    amax = 2 * math.pi * RIB['turns']
    half = RIB['thickness'] * .5
    rib = {}
    for name, theta in (('front', np.arcsin(s_c)), ('back', math.pi - np.arcsin(s_c))):
        a0 = theta - phi
        kk = np.round(((py - RIB['top']) / RIB['pitch'] * 2 * math.pi - a0) / (2 * math.pi))
        alpha = a0 + 2 * math.pi * kk
        dy = py - (RIB['top'] + RIB['pitch'] * alpha / (2 * math.pi))
        rng = smoothstep(0., .6, alpha) * smoothstep(amax, amax - .6, alpha)
        ed = np.abs(np.abs(dy) - half)
        line = np.exp(-(ed / 1.2) ** 2)
        body = smoothstep(half + .8, half - .8, np.abs(dy)) * .10
        gu = -alpha * 28. / (2 * math.pi) / 16.
        gv = dy / half * .72 * .5 + .5
        gly = sample(TG, gu, gv, True)[..., 0] * (np.abs(dy) < half)
        gain = 1. + .6 * s_c * s_c
        rib[name] = (line + body + gly) * gain * rng * ok
    ribbon = (rib['front'] + rib['back'] * .42 * (1. - .5 * sil)) * (.90 + .25 * fill)
    col += ribbon[..., None] * np.array([.60, .97, 1.])

    # Floating crystal shards.
    shard = np.zeros_like(px)
    for i, (sx, sy, sw, sh, tilt) in enumerate(SHARDS):
        cy = sy + 3. * math.sin(age * 1.1 + i * 1.7)
        a = tilt + .05 * math.sin(age * .8 + i)
        dx, dyy = px - sx, py - cy
        lx = dx * math.cos(a) + dyy * math.sin(a)
        ly = -dx * math.sin(a) + dyy * math.cos(a)
        q = np.abs(lx) / sw + np.abs(ly) / sh
        inside = 1 - smoothstep(.96, 1.04, q)
        edge = np.exp(-((q - 1) / .07) ** 2)
        ridge = np.exp(-(lx / 1.3) ** 2) * inside
        cross = np.exp(-((ly - .18 * sh) / 1.3) ** 2) * inside * .5
        shade = inside * (.30 + .36 * (lx > 0) * (1 - np.abs(ly) / sh) + .18 * (ly < 0))
        halo = np.exp(-np.maximum(q - 1, 0) * 4.) * .16
        shard += edge * 1.05 + ridge * .6 + cross + shade + halo
    col += (shard * (.8 + .4 * fill))[..., None] * np.array([.50, .95, 1.])

    # Rising sparks.
    for layer, (cell, speed) in enumerate(((22., 26.), (37., 17.))):
        gx, gy = px / cell, (py + age * speed) / cell
        ix, iy = np.floor(gx), np.floor(gy)
        hsh = np.modf(np.sin(ix * 127.1 + iy * 311.7 + layer * 74.7) * 43758.5453)[0] % 1.
        hx = np.modf(np.sin(ix * 269.5 + iy * 183.3) * 43758.5453)[0] % 1.
        hy = np.modf(np.sin(ix * 419.2 + iy * 371.9) * 43758.5453)[0] % 1.
        ddx, ddy = (gx - ix - (.2 + .6 * hx)) * cell, (gy - iy - (.2 + .6 * hy)) * cell
        dens = (.012 + .035 * fill + .08 * burst) * env * charged
        spark = np.exp(-(ddx * ddx + ddy * ddy) / 3.) * (hsh > 1 - dens) * (.6 + .4 * np.sin(age * 9. + hsh * 40.))
        col += spark[..., None] * np.array([.6, 1., 1.])
    # Translucent coverage, as in the material: glass occludes, light keeps its colour.
    col = sat(col)
    body = BODY_OPACITY * (sil * (.70 + .20 * mix) + (1 - sil) * sat(base_lum * 2.2))
    body = np.maximum(body, glow * (1 - sil) * .08 * BODY_OPACITY)
    cov = sat(np.maximum(body, col.max(2)))
    # Premultiplied RGB (= colour/alpha * alpha) plus alpha: composite as rgb + bg * (1 - a).
    return np.dstack([col * reveal, cov * reveal])


BODY_OPACITY = .85


def render_ss(fill, age, scale, factor=3.):
    """Supersample then area-filter, standing in for the GPU mip chain at small HUD sizes."""
    hi = render(fill, age, res=min(1., scale * factor))
    w, h = int(round(SIZE[0] * scale)), int(round((SIZE[1] - QUAD_TOP) * scale))
    return cv2.resize(hi, (w, h), interpolation=cv2.INTER_AREA)


def over(canvas, disp, ox, oy):
    """Place a premultiplied RGBA render onto an RGB canvas (Slate translucent blend)."""
    hh, ww = disp.shape[:2]
    ys = slice(max(oy, 0), min(oy + hh, canvas.shape[0]))
    xs = slice(max(ox, 0), min(ox + ww, canvas.shape[1]))
    d = disp[ys.start - oy:ys.stop - oy, xs.start - ox:xs.stop - ox]
    canvas[ys, xs] = d[..., :3] + canvas[ys, xs] * (1 - d[..., 3:4])
    return canvas


def concept_sheet():
    tmp = Path(os.environ['TEMP']) / 'azure_v10'
    tmp.mkdir(exist_ok=True)
    ref = Image.open(ROOT / 'Reference/azure-dragon-energy-concept-v10.jpg').convert('RGB')
    bg = np.array([16, 24, 27], np.float32) / 255.
    tiles = []
    for fill, box in ((1 / 9, (668, 70, 788, 472)), (5 / 9, (782, 70, 902, 472)), (1., (896, 70, 1016, 472))):
        r = ref.crop(box).resize((360, 1206), Image.LANCZOS)
        # Concept horn->apex ~370 px at 3x crop scale; texture horn (51.7) -> apex span.
        sc = 1110. / (LEVELS[0] - 51.7)
        disp = render_ss(fill, 1.7, sc)
        canvas = np.ones((1206, 360, 3), np.float32) * bg
        ox, oy = int(175 - CENTER * sc), int(1200 - (LEVELS[0] - QUAD_TOP) * sc)
        tiles += [np.asarray(r).astype(np.float32) / 255., sat(over(canvas, disp, ox, oy))]
    sheet = np.concatenate([np.pad(t, ((0, 0), (0, 8), (0, 0))) for t in tiles], 1)
    Image.fromarray((sheet * 255).astype(np.uint8)).save(tmp / 'hud_vs_concept.png')
    # In-game placement check against the concept's left panel (original bar inpainted away).
    scene = np.asarray(ref).copy()
    panel = scene[:, :665].copy()
    lum = panel.max(2)
    mask = np.zeros(lum.shape, np.uint8)
    mask[10:476, 30:200] = (lum[10:476, 30:200] > 70).astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
    clean = cv2.inpaint(panel, mask, 9, cv2.INPAINT_TELEA).astype(np.float32) / 255.
    sc = 400. / (LEVELS[0] - 51.7)
    bar = render_ss(.95, 2.3, sc)
    ox, oy = int(109 - CENTER * sc), int(430 - (LEVELS[0] - QUAD_TOP) * sc)
    out = over(clean.copy(), bar, ox, oy)
    both = np.concatenate([panel.astype(np.float32) / 255., np.zeros((576, 8, 3)), sat(out)], 1)
    Image.fromarray((both * 255).astype(np.uint8)).save(tmp / 'hud_ingame_vs_concept.png')
    # Readability over a bright daylight backdrop: old additive light vs the translucent body.
    sky = np.dstack([np.linspace(.78, .55, 576)[:, None].repeat(300, 1)] * 3).astype(np.float32) * np.array([.92, .96, 1.])
    bar = render_ss(5 / 9, 2.3, sc)
    ox2 = int(150 - CENTER * sc)
    old = sky.copy()
    hh, ww = bar.shape[:2]
    ys, xs = slice(max(oy, 0), min(oy + hh, 576)), slice(max(ox2, 0), min(ox2 + ww, 300))
    old[ys, xs] += bar[ys.start - oy:ys.stop - oy, xs.start - ox2:xs.stop - ox2, :3]
    new = over(sky.copy(), bar, ox2, oy)
    Image.fromarray((np.concatenate([sat(old), np.zeros((576, 8, 3)), sat(new)], 1) * 255).astype(np.uint8)).save(tmp / 'hud_bright_old_vs_new.png')
    if len(sys.argv) > 1:
        full = render(float(sys.argv[1]), 1.7)
        Image.fromarray((sat(over(np.ones(full.shape[:2] + (3,), np.float32) * bg, full, 0, 0)) * 255).astype(np.uint8)).save(tmp / 'hud_full_res.png')


if __name__ == '__main__':
    concept_sheet()
    print('preview written')
