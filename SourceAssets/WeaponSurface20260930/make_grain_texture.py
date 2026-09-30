"""Generate the shared tileable surface grain texture (plain CPython + numpy + PIL).

T_WS_Grain.png, 1024x1024 RGBA, linear data, one tile = GrainTileCm in object space:
  R  fine isotropic grain   (0.1-0.4 mm features: blast / phosphate crystal response)
  G  broad mottling         (5-15 mm features: finish and handling non-uniformity)
  B  hairline scratches     (sparse, anti-aliased, random orientation, 3-20 mm long)
  A  cellular stipple/pits  (0.5-1.5 mm cells: polymer texture, dust speckle)
Every channel is periodic, so triplanar tiling shows no seams.
Also writes T_WS_MaskNeutral.png (edge 0, cavity 0, AO 1, handling 0).
"""
from pathlib import Path
import numpy as np
from PIL import Image

O = Path(__file__).parent / 'Textures'
O.mkdir(exist_ok=True)
N = 1024
rng = np.random.default_rng(1930)


def band_noise(low, high):
    """Periodic noise with energy between `low` and `high` cycles per tile."""
    white = rng.standard_normal((N, N))
    f = np.fft.fftfreq(N) * N
    r = np.sqrt(f[None, :] ** 2 + f[:, None] ** 2)
    window = np.exp(-((np.log(np.maximum(r, 1e-6)) - np.log(np.sqrt(low * high))) ** 2) /
                    (2 * (np.log(high / low) / 2.5) ** 2))
    window[0, 0] = 0
    field = np.real(np.fft.ifft2(np.fft.fft2(white) * window))
    field -= field.mean()
    return field / (field.std() + 1e-9)


def to_unit(field, spread=0.17):
    """Map a unit-variance field to 0..1 around 0.5."""
    return np.clip(0.5 + field * spread, 0, 1)


fine = to_unit(0.8 * band_noise(160, 420) + 0.45 * band_noise(60, 160), 0.16)
mottle = to_unit(band_noise(3, 9) + 0.5 * band_noise(9, 22), 0.15)

# Hairline scratches: supersampled segments with wrap-around, soft falloff.
scratch = np.zeros((N, N), np.float32)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
for _ in range(95):
    cx, cy = rng.uniform(0, N, 2)
    ang = rng.uniform(0, np.pi)
    length = rng.uniform(55, 330)
    width = rng.uniform(0.45, 1.1)
    strength = rng.uniform(0.35, 1.0)
    d = np.array([np.cos(ang), np.sin(ang)], np.float32)
    dx = (xx - cx + N / 2) % N - N / 2
    dy = (yy - cy + N / 2) % N - N / 2
    along = dx * d[0] + dy * d[1]
    across = -dx * d[1] + dy * d[0]
    taper = np.clip(1 - np.abs(along) / (length / 2), 0, 1) ** 0.6
    line = np.exp(-(across / width) ** 2) * taper * strength
    scratch = np.maximum(scratch, line.astype(np.float32))
scratch = np.clip(scratch, 0, 1)

# Cellular stipple: periodic Worley F1 on a jittered grid.
cells = 88
jitter = rng.uniform(0.1, 0.9, (cells, cells, 2))
gx, gy = (xx + 0.5) / (N / cells), (yy + 0.5) / (N / cells)
ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
best = np.full((N, N), 1e9, np.float32)
for jy in (-1, 0, 1):
    for jx in (-1, 0, 1):
        cx, cy = ix + jx, iy + jy
        j = jitter[cy % cells, cx % cells]
        d2 = (gx - (cx + j[..., 0])) ** 2 + (gy - (cy + j[..., 1])) ** 2
        best = np.minimum(best, d2.astype(np.float32))
cell = np.sqrt(best)
stipple = np.clip(1 - cell / 0.75, 0, 1) ** 1.5
stipple = 0.25 + 0.75 * stipple * to_unit(band_noise(40, 90), 0.25)

rgba = np.stack([fine, mottle, scratch, np.clip(stipple, 0, 1)], -1)
Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA').save(O / 'T_WS_Grain.png')
neutral = np.zeros((4, 4, 4), np.uint8)
neutral[..., 2] = 255
Image.fromarray(neutral, 'RGBA').save(O / 'T_WS_MaskNeutral.png')
Image.fromarray(np.full((4, 4, 3), 255, np.uint8), 'RGB').save(O / 'T_WS_White.png')
Image.fromarray(np.full((4, 4), 128, np.uint8), 'L').save(O / 'T_WS_GreyLinear.png')
stats = {k: [float(v.mean()), float(v.std())] for k, v in
         {'fine': fine, 'mottle': mottle, 'scratch': scratch, 'stipple': stipple}.items()}
print('GRAIN_WRITTEN', stats)
