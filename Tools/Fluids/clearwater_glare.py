"""Compute the lens-aperture diffraction profile that gives Clearwater its sun stars.

Clearwater's most distinctive post effect is that every sun glint wears the diffraction
pattern of the camera aperture (index.html "Lens diffraction glare", lines 626-775). It
builds a round lens with a slightly flattened hexagonal edge, two hairline scratches and a
few dust specks, takes the FFT to get the far-field PSF, and integrates that over eight
visible wavelength bands so the spikes carry faint rainbow tints. Each frame it convolves
the bright pass with that kernel.

An FFT convolution per frame is not available to a post-process material. But the kernel
itself is a *static image*, so it is baked here once and shipped as a texture. The material
then does the cheaper half: a wide sparse tap ring on the bright pass, tinted per channel,
which reproduces the spikes and their colour fringing without a per-frame FFT.

Output: a 1D radial profile (for cheap multi-tap sampling) plus the full 2D kernel preview.
    python Tools/Fluids/clearwater_glare.py
"""
import argparse
import cmath
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
OUT = ASSETS / 'glare'

# clearwater buildPSF() (lines 688-723): aperture radius as a fraction of the grid,
# 3x3 supersampling, hexagon flats, scratches, dust.
APERTURE_FRACTION = 0.11
SUPERSAMPLE = 3
# Wavelength bands and their linear RGB weights, copied from buildPSF().
BANDS = (
    (440, (0.10, 0.00, 0.85)),
    (470, (0.00, 0.15, 1.00)),
    (500, (0.00, 0.60, 0.55)),
    (530, (0.05, 1.00, 0.15)),
    (560, (0.45, 0.95, 0.00)),
    (590, (0.95, 0.55, 0.00)),
    (620, (1.00, 0.20, 0.00)),
    (650, (0.70, 0.05, 0.00)),
)
REFERENCE_WAVELENGTH = 550.0
# clearwater lifts the far field relative to the core: phone lenses flare harder than an
# ideal aperture (line 719).
FARFIELD_LIFT_START = 3.0
FARFIELD_LIFT_SPAN = 30.0
FARFIELD_LIFT_GAIN = 7.0


def fft2(a):
    """2D FFT via numpy (clearwater hand-rolls fft2 for the browser; numpy is fine here)."""
    return np.fft.fft2(a)


def build_aperture(n):
    """The aperture mask, with the hexagon flats, scratches and dust of the source."""
    R = n * APERTURE_FRACTION
    D = math.pi / 180.0
    flats = [(15 + k * 60) * D for k in range(6)]
    scratches = [(21 * D, 0.12 * R, 2.2), (22.5 * D, -0.38 * R, 1.6), (19 * D, 0.55 * R, 1.2),
                 (152 * D, 0.25 * R, 1.0), (84 * D, -0.2 * R, 0.8)]
    r2 = np.random.default_rng(3)
    dust = [((r2.random() - 0.5) * 1.4 * R, (r2.random() - 0.5) * 1.4 * R,
             (0.015 + 0.03 * r2.random()) * R) for _ in range(7)]

    acc = np.zeros((n, n), dtype=np.float64)
    for sy in range(SUPERSAMPLE):
        for sx in range(SUPERSAMPLE):
            yy, xx = np.mgrid[0:n, 0:n]
            dx = xx - n / 2 + (sx + 0.5) / SUPERSAMPLE - 0.5
            dy = yy - n / 2 + (sy + 0.5) / SUPERSAMPLE - 0.5
            inside = (dx * dx + dy * dy) <= R * R
            for f in flats:
                inside &= (dx * math.cos(f) + dy * math.sin(f)) <= R * 0.955
            for a, o, w in scratches:
                inside &= np.abs(dx * math.cos(a) + dy * math.sin(a) - o) >= w * 0.5
            for ddx, ddy, dr in dust:
                inside &= ((dx - ddx) ** 2 + (dy - ddy) ** 2) >= dr * dr
            acc += inside
    return acc / (SUPERSAMPLE * SUPERSAMPLE)


def psf_from_aperture(mask):
    """Far-field intensity = |FFT(aperture)|^2, fftshifted so DC sits at the centre."""
    field = fft2(mask)
    return np.abs(np.fft.fftshift(field)) ** 2


def sample_bilinear(img, u, v):
    n = img.shape[0]
    u = np.clip(u, 0, n - 1.001)
    v = np.clip(v, 0, n - 1.001)
    x0 = np.floor(u).astype(np.int64)
    y0 = np.floor(v).astype(np.int64)
    fx = u - x0
    fy = v - y0
    return ((img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx) * (1 - fy)
            + (img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx) * fy)


def chromatic_psf(psf, out_size):
    """Integrate the PSF over the visible bands; shorter wavelengths scale the pattern up.

    This is the step that makes the spikes carry colour: each band's diffraction pattern is
    a scaled copy of the same kernel, so the blue spike is slightly narrower than the red.
    """
    n = psf.shape[0]
    acc = np.zeros((out_size, out_size, 3), dtype=np.float64)
    yy, xx = np.mgrid[0:out_size, 0:out_size]
    for lam, w in BANDS:
        s = lam / REFERENCE_WAVELENGTH
        u = (n / 2 + (xx - out_size / 2) / s)
        v = (n / 2 + (yy - out_size / 2) / s)
        v_psf = sample_bilinear(psf, u, v) / (s * s)
        for c in range(3):
            acc[:, :, c] += v_psf * w[c]
    return acc


def radial_profile(kernel, bins):
    """Azimuthally averaged profile, plus the per-channel ratios that tint the spikes.

    A post-process material cannot afford the full 2D convolution, so it samples this
    profile along a wide sparse ring. Averaging azimuthally keeps the rings circular, which
    is what a round aperture actually produces.
    """
    n = kernel.shape[0]
    cy = cx = n / 2.0
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - cx, yy - cy)
    rmax = n / 2.0
    idx = np.clip((r / rmax * (bins - 1)).astype(np.int64), 0, bins - 1)
    prof = np.zeros((bins, 3), dtype=np.float64)
    count = np.bincount(idx.ravel(), minlength=bins).astype(np.float64)
    for c in range(3):
        prof[:, c] = np.bincount(idx.ravel(), weights=kernel[:, :, c].ravel(),
                                 minlength=bins) / np.maximum(count, 1.0)
    return prof, rmax


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--size', type=int, default=512, help='PSF grid size (clearwater uses 512)')
    ap.add_argument('--bins', type=int, default=64, help='radial profile bins')
    ap.add_argument('--preview', type=int, default=256, help='2D kernel preview size')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    mask = build_aperture(args.size)
    psf = psf_from_aperture(mask)
    kern = chromatic_psf(psf, args.preview)

    # Far-field lift, matching buildPSF()'s "phone lenses flare harder" term.
    n2 = args.preview
    yy, xx = np.mgrid[0:n2, 0:n2]
    rr = np.hypot(xx - n2 / 2.0, yy - n2 / 2.0)
    lift = 1.0 + FARFIELD_LIFT_GAIN * np.clip(
        (rr - FARFIELD_LIFT_START) / FARFIELD_LIFT_SPAN, 0.0, 1.0)
    kern *= lift[:, :, None]

    # Normalise per channel so the kernel redistributes energy instead of adding it.
    for c in range(3):
        s = kern[:, :, c].sum()
        if s > 0:
            kern[:, :, c] /= s

    prof, rmax = radial_profile(kern, args.bins)
    # Normalise the profile to its peak so the material can use it as a pure shape term.
    peak = max(prof.max(), 1e-12)
    prof_n = prof / peak

    (OUT / 'glare_profile.json').write_text(json.dumps({
        'source': 'clearwater index.html buildPSF()',
        'bands_nm': [b[0] for b in BANDS],
        'aperture_fraction': APERTURE_FRACTION,
        'supersample': SUPERSAMPLE,
        'reference_wavelength_nm': REFERENCE_WAVELENGTH,
        'bins': args.bins,
        'psf_size': args.size,
        'peak_to_mean_ratio': float(prof.max() / max(prof.mean(), 1e-12)),
        'core_to_farfield_ratio': float(prof.max() / max(prof[-1].max(), 1e-12)),
        'profile_rgb': [[round(float(v), 8) for v in row] for row in prof_n],
    }, indent=2), encoding='utf-8')

    if Image is not None:
        # Preview only: the kernel spans ~5 orders of magnitude from core to spike tip, so a
        # gamma curve is needed to see the star at all. The imported texture stays linear.
        lo = max(np.percentile(kern, 40.0), 1e-12)
        hi = max(np.percentile(kern, 99.99), lo * 10.0)
        p = np.clip((kern - lo) / (hi - lo), 0.0, 1.0) ** (1.0 / 2.4)
        Image.fromarray((p * 255.0).astype(np.uint8)).save(OUT / 'glare_kernel.png')
        Image.fromarray((np.clip(prof_n, 0, 1) * 255.0).astype(np.uint8)).resize(
            (args.bins * 4, 120), Image.NEAREST).save(OUT / 'glare_profile.png')

    print('CLEARWATER_GLARE ' + json.dumps({
        'psf_size': args.size,
        'bins': args.bins,
        'peak_to_mean': round(float(prof.max() / max(prof.mean(), 1e-12)), 2),
        'core_to_farfield': round(float(prof.max() / max(prof[-1].max(), 1e-12)), 2),
        'out': str(OUT),
    }))


if __name__ == '__main__':
    main()
