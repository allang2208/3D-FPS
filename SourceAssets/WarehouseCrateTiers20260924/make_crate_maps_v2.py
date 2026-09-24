"""Regenerate the five crate surface/normal map pairs with a quality pass (v2).

Diagnosis from the in-game screenshot: v1 maps read as "static noise" 鈥?too much
high-frequency amplitude, no directional structure, and the material graph ignored
the fine channel. v2 keeps the same channel contract (R broad albedo, G fine albedo,
B roughness; tangent normal map) but:

  wood   : directional grain along the planks + per-plank tint/phase + seam grooves
  stone  : soft blocky mottling, sparse hairline cracks, low speckle
  iron   : long brushed streaks, sparse shallow pits, mid roughness
  gold   : smooth faceted waviness, fine sparkle, low roughness
  silver : very smooth two-direction brushed microstructure, lowest roughness

Seamless via periodic value/FBM noise (FFT-free, hash lattice). Deterministic seeds.
2048^2 PNGs. No renders/tests 鈥?stats only.
"""
import numpy as np
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
OUT = HERE / 'Textures'
OUT.mkdir(exist_ok=True)
SIZE = 2048

def rng(seed): return np.random.default_rng(seed)

def lattice(r, shape):
    return r.random(shape)

def smooth_periodic(field, up):
    """Bilinear-upsample a periodic lattice to SIZE (wraps -> seamless)."""
    h, w = field.shape
    y = np.mod(np.arange(SIZE) * h / SIZE, h)
    x = np.mod(np.arange(SIZE) * w / SIZE, w)
    y0 = np.floor(y).astype(int); x0 = np.floor(x).astype(int)
    y1 = (y0 + 1) % h; x1 = (x0 + 1) % w
    fy = (y - y0)[:, None]; fx = (x - x0)[None, :]
    a = field[np.ix_(y0, x0)]; b = field[np.ix_(y0, x1)]
    c = field[np.ix_(y1, x0)]; d = field[np.ix_(y1, x1)]
    # smoothstep for softer cells
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def fbm(r, cells_min, octaves, up=SIZE):
    """Periodic fBm; cells_min = cells of the coarsest octave (square lattice)."""
    acc = np.zeros((SIZE, SIZE)); norm = 0.0; cells = cells_min; amp = 1.0
    for _ in range(octaves):
        cells = max(2, int(round(cells)))
        acc += amp * smooth_periodic(lattice(r, (cells, cells)), up)
        norm += amp; amp *= 0.5; cells *= 2
    return acc / norm

def aniso(r, cells_x, cells_y, octaves):
    """Directional fBm with rectangular lattices (stretched along y when cells_x<cells_y)."""
    acc = np.zeros((SIZE, SIZE)); norm = 0.0
    cx, cy = cells_x, cells_y; amp = 1.0
    for _ in range(octaves):
        acc += amp * smooth_periodic(lattice(r, (max(2, int(round(cy))), max(2, int(round(cx))))), up=SIZE)
        norm += amp; amp *= 0.5; cx *= 2; cy *= 2
    return acc / norm

def _box_blur_periodic(a, k):
    """Periodic box blur, radius k, by direct shifted sums (small k -> cheap, always correct)."""
    if k <= 0:
        return a
    acc = np.zeros_like(a, dtype=np.float64)
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            acc += np.roll(np.roll(a, dy, axis=0), dx, axis=1)
    return acc / float((2 * k + 1) ** 2)

def height_to_normal(h, strength, smooth=2):
    """Periodic central differences on a low-passed height -> tangent normal, RG encoded 0..1.

    The per-pixel derivative of raw high-frequency fBm is dominated by single-pixel jitter,
    which is what made v1 read as "static": a 2-3 px box pass first keeps the grain but
    drops the incoherent spikes. `strength` then scales the surviving gradient.
    """
    hh = _box_blur_periodic(h.astype(np.float64), smooth)
    dzdx = (np.roll(hh, -1, 1) - np.roll(hh, 1, 1)) * 0.5 * strength
    dzdy = (np.roll(hh, -1, 0) - np.roll(hh, 1, 0)) * 0.5 * strength
    n = np.stack([-dzdx, -dzdy, np.ones_like(hh)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n

def save_pair(name, broad, fine, rough, height, nstr):
    surf = np.stack([broad, fine, rough], axis=-1)
    nrm = height_to_normal(height, nstr)
    Image.fromarray((np.clip(surf, 0, 1) * 255 + 0.5).astype(np.uint8)).save(OUT / ('T_Crate_%s_Surface.png' % name))
    Image.fromarray((np.clip(nrm * 0.5 + 0.5, 0, 1) * 255 + 0.5).astype(np.uint8)).save(OUT / ('T_Crate_%s_Normal.png' % name))
    z = float(nrm[..., 2].mean())
    stats = {'surface_mean_rgb': [round(float(surf[..., i].mean()), 3) for i in range(3)],
             'normal_z_mean': round(z, 3)}
    print('MAP %s %s%s' % (name, stats, '' if z >= 0.90 else '  WARN_STEEP'), flush=True)

def to8(x): return np.clip(x, 0, 1)

# ---------------------------------------------------------------- wood
r = rng(1101)
plank_h = 0.25  # 4 planks per tile -> seamless band phase at tile wrap (~15.6 cm at tiling 1.6/m)
yy, xx = np.mgrid[0:SIZE, 0:SIZE] / SIZE
band = np.floor(yy / plank_h).astype(int) % 4
rb = rng(1102)
band_tint = rb.random(4)[band]
grain = aniso(r, 40, 3, 5)                      # stretched along x = plank direction
grain2 = aniso(r, 220, 6, 3)                    # fine fibre
wave = fbm(r, 6, 4)
seam = np.minimum((yy % plank_h), (plank_h - yy % plank_h)) / plank_h  # 0 at seams
seam_groove = np.clip(seam / 0.06, 0, 1)
broad = to8(0.52 + 0.16 * (wave - 0.5) + 0.10 * (band_tint - 0.5) + 0.10 * (grain - 0.5) - 0.22 * (1 - seam_groove))
fine = to8(0.50 + 0.34 * (grain - 0.5) + 0.16 * (grain2 - 0.5))
rough = to8(0.50 + 0.22 * (grain2 - 0.5) + 0.14 * (1 - seam_groove))
height = 0.5 * grain + 0.25 * grain2 + 0.35 * (1 - seam_groove)
save_pair('Wood', broad, fine, rough, height, 40)

# ---------------------------------------------------------------- stone
r = rng(2201)
blocks = fbm(r, 5, 4)
blotch = fbm(r, 14, 5)
speck = aniso(r, 400, 400, 2)
crack = np.clip((fbm(r, 24, 4) - 0.62) * 9, 0, 1)
crack = crack * crack * (3 - 2 * crack)  # smooth the ridge, no 1px cliffs
broad = to8(0.55 + 0.16 * (blocks - 0.5) + 0.10 * (blotch - 0.5) - 0.18 * crack)
fine = to8(0.50 + 0.20 * (speck - 0.5) + 0.10 * (blotch - 0.5))
rough = to8(0.78 + 0.12 * (speck - 0.5) + 0.08 * (blocks - 0.5))
height = 0.5 * blotch + 0.15 * speck - 0.25 * crack
save_pair('Stone', broad, fine, rough, height, 30)

# ---------------------------------------------------------------- iron (brushed)
r = rng(3301)
streak = aniso(r, 8, 512, 4)                    # long horizontal brushing
pit = np.clip((fbm(r, 90, 3) - 0.72) * 6, 0, 1)
broad = to8(0.52 + 0.10 * (streak - 0.5) - 0.10 * pit)
fine = to8(0.50 + 0.22 * (streak - 0.5))
rough = to8(0.44 + 0.16 * (streak - 0.5) + 0.22 * pit)
height = 0.6 * streak - 0.5 * pit
save_pair('Iron', broad, fine, rough, height, 22)

# ---------------------------------------------------------------- gold
r = rng(4401)
facet = fbm(r, 7, 4)
ripple = aniso(r, 30, 12, 4)
sparkle = aniso(r, 512, 512, 2)
broad = to8(0.55 + 0.12 * (facet - 0.5) + 0.08 * (ripple - 0.5))
fine = to8(0.50 + 0.18 * (ripple - 0.5) + 0.10 * (sparkle - 0.5))
rough = to8(0.28 + 0.12 * (facet - 0.5) + 0.08 * (sparkle - 0.5))
height = 0.5 * ripple + 0.3 * facet + 0.2 * sparkle
save_pair('Gold', broad, fine, rough, height, 18)

# ---------------------------------------------------------------- silver
r = rng(5501)
brush_x = aniso(r, 6, 700, 3)
brush_y = aniso(r, 700, 6, 3)
soft = fbm(r, 9, 4)
broad = to8(0.54 + 0.08 * (soft - 0.5) + 0.05 * (brush_x - 0.5))
fine = to8(0.50 + 0.12 * (brush_x - 0.5) + 0.12 * (brush_y - 0.5))
rough = to8(0.18 + 0.10 * (brush_x - 0.5) + 0.06 * (soft - 0.5))
height = 0.4 * brush_x + 0.4 * brush_y
save_pair('Silver', broad, fine, rough, height, 14)
print('MAPS_V2_DONE', flush=True)
