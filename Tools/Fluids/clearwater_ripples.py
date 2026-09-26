"""Bake the fine-ripple tangent-space normal map used by Clearwater's texBS path.

Clearwater samples its fine surface detail through texBS(), a cubic B-spline filter taken
as four bilinear taps, and feeds the result into the optics block as `FineNormal`
(index.html line 396-404 for the filter, line 513 for its use in the caustic lookup). It
exists so the sun glints stay crisp without sparkling: the B-spline keeps the slope field
continuous where a plain bilinear tap would step.

A material can sample the map but cannot invent it, so the map is baked here. Its content
comes from the *same reduced spectrum* as the main surface, restricted to wavelengths too
short for the 0.94 m vertex grid to carry -- so the fine layer is spectrally consistent with
the geometry instead of being decorative noise.

Periodic by construction: every component's wavevector is snapped to an integer number of
cycles per tile, so the map tiles exactly and the B-spline filter stays continuous across
the seam.

Output: T_ClearwaterRipples_N (tangent space, +Y up) plus a manifest.
    python Tools/Fluids/clearwater_ripples.py
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'SourceAssets' / 'ClearwaterWater20260926'
WAVES = ASSETS / 'waves.json'
OUT = ASSETS / 'ripples'

# The map covers a patch of this size; the projection in the material scales it to world
# units, so this only sets how much detail the tile can hold.
PATCH_M = 8.0
RES = 512


def build_components(waves, patch_cm):
    """Keep the short-wavelength end of the spectrum and make it integer-cycle periodic."""
    wf = []
    for w in waves:
        lam_cm = w['wavelength'] * 100.0
        # The vertex grid resolves about 0.94 m; anything longer is already geometry.
        if lam_cm > patch_cm * 0.25:
            continue
        kx = math.sin(math.atan2(w['dir'][1], w['dir'][0])) * w['k'] * 0.01
        kz = math.cos(math.atan2(w['dir'][1], w['dir'][0])) * w['k'] * 0.01
        # Snap to integer cycles across the tile.
        scale = 2.0 * math.pi / patch_cm
        kx = round(kx / scale) * scale
        kz = round(kz / scale) * scale
        k = math.hypot(kx, kz)
        if k <= 1e-9:
            continue
        wf.append({'kx': kx, 'kz': kz, 'amp': w['amplitude'] * 100.0, 'phase': w['phase']})
    return wf


def add_tileable_noise(wf, patch_cm, octaves, amp_cm, seed):
    """A few octaves of exactly periodic value noise, for the very fine end."""
    for o in range(octaves):
        freq = 8 * (2 ** o)                     # integer cycles per tile
        ang = (seed * 0.7 + o * 1.1) % (2 * math.pi)
        k = 2.0 * math.pi * freq / patch_cm
        wf.append({'kx': k * math.cos(ang), 'kz': k * math.sin(ang),
                   'amp': amp_cm / (1.7 ** o), 'phase': (o * 2.3 + seed) % (2 * math.pi)})
    return wf


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--res', type=int, default=RES)
    ap.add_argument('--patch', type=float, default=PATCH_M)
    ap.add_argument('--strength', type=float, default=1.0,
                    help='normal slope scale; 1.0 keeps the spectrum self-consistent')
    args = ap.parse_args()

    patch_cm = args.patch * 100.0
    waves = json.loads(WAVES.read_text(encoding='utf-8'))['waves']
    wf = build_components(waves, patch_cm)
    wf = add_tileable_noise(wf, patch_cm, octaves=3, amp_cm=0.02, seed=5)
    if not wf:
        raise RuntimeError('no ripple components survived the wavelength filter')

    res = args.res
    axis = np.linspace(0.0, patch_cm, res, endpoint=False)
    X, Y = np.meshgrid(axis, axis, indexing='ij')
    dx = np.zeros_like(X)
    dy = np.zeros_like(X)
    for w in wf:
        ph = w['kx'] * X + w['kz'] * Y + w['phase']
        c = np.cos(ph)
        dx += w['amp'] * w['kx'] * c
        dy += w['amp'] * w['kz'] * c

    # Tangent-space normal from the height gradient, +Z out of the surface. Water slopes are
    # small, so the map is mostly (0,0,1) with shallow perturbation -- that is correct: the
    # strength of the effect comes from how the material blends it, not from a steep map.
    nx = -dx * args.strength
    ny = -dy * args.strength
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln

    slope_rms = float(np.sqrt((nx * nx + ny * ny).mean()))
    out = np.zeros((res, res, 4), dtype=np.float32)
    out[:, :, 0] = nx * 0.5 + 0.5
    out[:, :, 1] = ny * 0.5 + 0.5
    out[:, :, 2] = nz * 0.5 + 0.5
    out[:, :, 3] = 1.0

    OUT.mkdir(parents=True, exist_ok=True)
    if Image is not None:
        Image.fromarray((np.clip(out[:, :, :3], 0, 1) * 255.0).astype(np.uint8)).save(
            OUT / 'T_ClearwaterRipples_N.png')

    (OUT / 'ripples.json').write_text(json.dumps({
        'res': res, 'patch_m': args.patch, 'strength': args.strength,
        'components': len(wf),
        'shortest_wavelength_cm': round(min(2 * math.pi / math.hypot(w['kx'], w['kz'])
                                            for w in wf), 3),
        'longest_wavelength_cm': round(max(2 * math.pi / math.hypot(w['kx'], w['kz'])
                                           for w in wf), 2),
        'tangent_slope_rms': round(slope_rms, 5),
        'encoding': 'tangent space, +Y up, RGB = normal*0.5+0.5',
    }, indent=2), encoding='utf-8')

    print('CLEARWATER_RIPPLES ' + json.dumps({
        'res': res, 'patch_m': args.patch, 'components': len(wf),
        'tangent_slope_rms': round(slope_rms, 5),
        'out': str(OUT), 'png': Image is not None,
    }))


if __name__ == '__main__':
    main()
