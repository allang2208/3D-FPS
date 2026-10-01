"""Produce original seamless packed energy-flow fields, without rendering."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/ThunderLanceFlux20261001')
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 1024, 256
rng = np.random.default_rng(20261001)
fx = np.fft.fftfreq(WIDTH) * WIDTH
fy = np.fft.fftfreq(HEIGHT) * HEIGHT


def octave(x_band, y_band):
    spectrum = np.fft.fft2(rng.normal(size=(HEIGHT, WIDTH)))
    filt = np.exp(-.5 * ((fx[None, :] / x_band) ** 2 + (fy[:, None] / y_band) ** 2))
    field = np.fft.ifft2(spectrum * filt).real
    return (field - field.mean()) / max(field.std(), 1e-6)


def normalized(field):
    low, high = np.percentile(field, [1, 99])
    return np.clip((field - low) / (high - low), 0, 1)


billows = normalized(octave(3, 3) + .52 * octave(8, 7) + .25 * octave(19, 15))
folds = normalized(octave(8, 5) + .5 * octave(22, 13) + .22 * octave(47, 24))
ridge_field = normalized(octave(5, 6) + .35 * octave(18, 17))
ridges = 1 - np.abs(ridge_field * 2 - 1)
pixels = np.round(np.stack([billows, folds, ridges], axis=-1) * 255).astype(np.uint8)
Image.fromarray(pixels).save(OUT / 'T_ThunderFluxFields.png')
(OUT / 'field-production.json').write_text(json.dumps({
    'source': 'original seeded spectral fields; no extracted game textures',
    'seed': 20261001, 'size': [WIDTH, HEIGHT], 'seamless_axes': ['U', 'V'],
    'channels': {'R': 'billowing density', 'G': 'rolling folds', 'B': 'energy ridges'},
    'srgb': False, 'mips': True, 'rendered': False}, indent=2), encoding='utf-8')
print('THUNDER_FLUX_FIELDS_BAKED')
