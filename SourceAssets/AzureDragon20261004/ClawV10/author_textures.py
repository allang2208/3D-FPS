"""Claw V10.1 surface textures extracted from the approved reference claws (Bailian sources).

Veins:  claw_002 palm/forearm interior -> tileable RGB (R fine vein lines, G body haze, B full luma).
Smoke:  claw_001 upper-right smoke    -> rotated so the flow runs along +U, tileable along U
        (R luma, G soft density, B bright filaments).
Writes Export/T_AzureDragonClawVeins.png, Export/T_AzureDragonClawSmoke.png and tiled previews.
"""
import sys
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / 'HudV10' / 'Generated'
OUT = ROOT / 'Export'
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW = Path(sys.argv[sys.argv.index('--preview') + 1]) if '--preview' in sys.argv else None


def luma(img):
    rgb = img[..., :3].astype(np.float32) / 255.
    return rgb[..., 0] * .2126 + rgb[..., 1] * .7152 + rgb[..., 2] * .0722


def norm(x, lo=1., hi=99.5):
    a, b = np.percentile(x, lo), np.percentile(x, hi)
    return np.clip((x - a) / max(1e-5, b - a), 0., 1.)


def window(n, edge):
    t = np.linspace(0., 1., n, dtype=np.float32)
    s = lambda a, b, x: np.clip((x - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((x - a) / (b - a), 0, 1))
    return s(0., edge, t) * s(1., 1. - edge, t)


def tile_u(c, edge=.22):
    # The rolled copy's seam sits in the middle, exactly where the original is fully weighted.
    w = c.shape[1]
    shifted = np.roll(c, w // 2, 1)
    m = window(w, edge)[None, :, None]
    return c * m + shifted * (1. - m)


def tile_2d(c, edge=.18):
    # Sequential 1D passes: the second pass blends copies that are already seamless in U.
    return np.transpose(tile_u(np.transpose(tile_u(c, edge), (1, 0, 2)), edge), (1, 0, 2))


def save(name, rgb):
    cv2.imwrite(str(OUT / name), cv2.cvtColor((np.clip(rgb, 0, 1) * 255. + .5).astype(np.uint8), cv2.COLOR_RGB2BGR))


# ---- veins ---------------------------------------------------------------------------------
src = cv2.cvtColor(cv2.imread(str(SRC / 'claw_002.png'), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
crop = src[1110:1710, 1090:1690]  # interior of the palm/forearm, no background
L = luma(crop)
# Knuckle glints would repeat as dots every tile; the material adds its own joint highlights.
L = np.minimum(L, np.percentile(L, 98.5))
L = cv2.resize(L, (1024, 1024), interpolation=cv2.INTER_LANCZOS4)
blur = cv2.GaussianBlur(L, (0, 0), 14.)
fine = norm(np.maximum(0., L - blur), 2., 99.6) ** .85
haze = norm(cv2.GaussianBlur(L, (0, 0), 22.), 1., 99.)
veins = tile_2d(np.dstack([fine, haze, norm(L)]))
# Compact white glints (a knuckle socket in the source) read as a repeating "eye"; inpaint them
# on a wrap-padded copy so the result stays seamless.
white = ((veins[..., 0] > .9) & (veins[..., 2] > .85)).astype(np.uint8)
count, labels, stats, _ = cv2.connectedComponentsWithStats(white)
mask = np.zeros_like(white)
for i in range(1, count):
    x, y, bw, bh, area = stats[i]
    if bw < 48 and bh < 48 and 120 < area < 800:
        cv2.circle(mask, (int(x + bw / 2), int(y + bh / 2)), int(max(bw, bh) * .9) + 6, 1, -1)
pad = 64
padded = np.pad((np.clip(veins, 0, 1) * 255).astype(np.uint8), ((pad, pad), (pad, pad), (0, 0)), mode='wrap')
mpad = np.pad(mask, pad, mode='wrap')
veins = cv2.inpaint(padded, mpad, 9, cv2.INPAINT_TELEA)[pad:-pad, pad:-pad].astype(np.float32) / 255.
save('T_AzureDragonClawVeins.png', veins)

# ---- smoke ---------------------------------------------------------------------------------
src = cv2.cvtColor(cv2.imread(str(SRC / 'claw_001.png'), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
region = src[0:820, 940:1809]
L = luma(region)
h, w = L.shape
# The reference smoke rises toward the upper right (~58 deg); rotate so it flows along +U.
rot = cv2.getRotationMatrix2D((w / 2., h / 2.), -58., 1.)
L = cv2.warpAffine(L, rot, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
cy, cx = h // 2, w // 2
L = L[cy - 190:cy + 190, cx - 380:cx + 380]
L = cv2.resize(L, (1024, 512), interpolation=cv2.INTER_LANCZOS4)
L = cv2.bilateralFilter(L, 9, .08, 5.)  # the source grain would be amplified by the high-pass
L = cv2.GaussianBlur(L, (0, 0), 1.6)
density = norm(cv2.GaussianBlur(L, (0, 0), 10.), 2., 99.5)
filaments = norm(np.maximum(0., L - cv2.GaussianBlur(L, (0, 0), 7.)), 8., 99.6) ** 1.15
smoke = tile_u(np.dstack([norm(L, 2., 99.6), density, filaments]))
save('T_AzureDragonClawSmoke.png', smoke)

if PREVIEW:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    tint = np.array([.25, 1., .95], np.float32)
    v = np.tile(veins, (2, 2, 1))
    cv2.imwrite(str(PREVIEW / 'veins_tiled.png'),
                cv2.cvtColor((np.clip(v[..., :1] * tint + v[..., 1:2] * tint * .25, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    s = np.tile(smoke, (1, 2, 1))
    cv2.imwrite(str(PREVIEW / 'smoke_tiled.png'),
                cv2.cvtColor((np.clip(s[..., :1] * tint * .8 + s[..., 2:3] * .5, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
print('AZURE_CLAW_TEXTURES_V101', 'veins', veins.shape, 'smoke', smoke.shape, flush=True)
