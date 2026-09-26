"""Bake Clearwater-style refracted-sun caustics to a seamlessly looping texture sequence.

Clearwater (https://github.com/Aureliengmz/clearwater, MIT) computes caustics every frame by
rasterising a projected grid through the wave surface with a per-channel IOR, then reading
the screen-space Jacobian of the refracted source coordinates as light intensity
(index.html pCaus / renderCaustics, lines 283-340). That needs a per-frame vertex shader
pass; a material cannot do it, and this project has no custom render pass.

So the same physics is evaluated offline instead, backwards:

    for every point on the surface grid
        height   = reduced Clearwater spectrum, tiled periodically over the patch
        normal   = analytic gradient of that height field
        refracted = refract(-sun, normal, 1/IOR)
        landing   = where that ray meets the seabed plane, expressed in patch UV

Each ray deposits energy into the texel it lands on. Where the surface focuses light the
rays converge and the texel accumulates far more than average: that convergence *is* the
caustic web, which is why this back-projection matches the source's forward one.

Per-channel IOR is kept, so the three colour channels focus at slightly different places and
the result carries the source's faint dispersion fringes.

Seamlessness: the wave field is made exactly periodic over the patch by quantising each
component's wavevector to integer cycles per patch, so the baked sequence tiles. Frames are
baked across one Clearwater loop (60 s, from buildH0's dispersion quantisation) and the last
frame continues into the first.

Output: 32 frames x 512 x 512, PNG + a manifest. Run standalone:
    python Tools/Fluids/clearwater_caustics.py
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

try:
    from PIL import Image
except ImportError:  # only needed for the PNG dump
    Image = None

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'SourceAssets' / 'ClearwaterWater20260926'
WAVES = ASSETS / 'waves.json'
OUT = ASSETS / 'caustics'

# clearwater IORS (index.html line 322): per-channel refraction index around 1.333.
IORS = (1.3315, 1.3335, 1.3365)
# clearwater DEPTH (line 130) and the sun it renders with (lines 817-818).
DEPTH_M = 1.6
SUN_EL_DEG = 31.0
SUN_AZ_DEG = 6.0
LOOP_SECONDS = 60.0
FRAMES = 32
RES = 512
# Rays per bake. More rays means a smoother, less speckled caustic; the run is offline.
SURFACE_GRID = 640


def quantise_periodic(waves, patch):
    """Snap each component to an integer number of cycles per patch so the bake tiles.

    clearwater does not need this because its FFT grid is periodic by construction; the
    reduced 48-component sum is not, so a small shift in wavenumber is traded for
    seamlessness. Direction is nearest-axis snapped as well, keeping the wind spread while
    making the phase exactly periodic in both patch axes.
    """
    out = []
    for w in waves:
        kx = w['dir'][0] * w['k'] * 0.01   # rad/cm
        kz = w['dir'][1] * w['k'] * 0.01
        # cycles across the patch
        cx = kx * patch / (2.0 * math.pi)
        cz = kz * patch / (2.0 * math.pi)
        cx = round(cx) / (patch / (2.0 * math.pi))
        cz = round(cz) / (patch / (2.0 * math.pi))
        k = math.hypot(cx, cz)
        if k <= 1e-9:
            continue
        out.append({'kx': cx, 'kz': cz, 'k': k, 'amp': w['amplitude'] * 100.0,
                    'omega': w['omega'], 'phase': w['phase']})
    return out


def surface_height(wf, X, Y, t):
    """Metres of displacement over the patch."""
    z = np.zeros_like(X)
    dx = np.zeros_like(X)
    dy = np.zeros_like(X)
    for w in wf:
        ph = w['kx'] * X + w['kz'] * Y + w['phase'] - w['omega'] * t
        s = np.sin(ph)
        c = np.cos(ph)
        z += w['amp'] * s
        dx += w['amp'] * w['kx'] * c
        dy += w['amp'] * w['kz'] * c
    return z, dx, dy


def refract_all(sun, n):
    """Vector refraction of the sun direction through a unit normal, or None where it TIRs."""
    cosi = -np.dot(n, sun)                      # n . (-sun)
    eta = 1.0 / IORS[1]
    k = 1.0 - eta * eta * (1.0 - cosi * cosi)
    ok = k >= 0.0
    k = np.sqrt(np.maximum(k, 0.0))
    r = eta * sun + (eta * cosi - k) * n
    return r, ok


def bake_frame(wf, t, res, patch, grid, smooth_texels=0.6):
    """One frame of the caustic sequence, per channel.

    Intensity is the light *concentration*, not the ray count. Clearwater gets this from the
    screen-space Jacobian of the refracted source coordinates (index.html pCaus fragment
    shader: area = |dFdx(vSrc) x dFdy(vSrc)|). The equivalent here is the Jacobian of the
    landing-position map, sampled on the same grid:

        I = 1 / |det J|,  J = d(landing) / d(surface)

    det J < 1 means neighbouring rays converged, so the light is brighter. Accumulating raw
    ray counts instead only measures how many grid samples fell in a texel, which is nearly
    uniform and washes the web out to a flat ~2x.
    """
    axis = np.linspace(0.0, patch, grid, endpoint=False)
    X, Y = np.meshgrid(axis, axis, indexing='ij')
    z, dx, dy = surface_height(wf, X, Y, t)
    step = patch / grid

    # Surface normal from the height gradient (clearwater: n = normalize(-dh/dx, 1, -dh/dz)).
    nz = np.ones_like(dx)
    nl = np.sqrt(dx * dx + dy * dy + nz * nz)
    nx = -dx / nl
    ny = -dy / nl
    nzv = nz / nl

    el = math.radians(SUN_EL_DEG)
    az = math.radians(SUN_AZ_DEG)
    # clearwater's frame: y up, camera toward -z; az measured off the view axis.
    sun = np.array([math.sin(az) * math.cos(el), math.sin(el), -math.cos(az) * math.cos(el)])

    # Kernel wide enough to bridge one ray spacing so the deposit has no holes, but far
    # narrower than the caustic web itself.
    sigma_cm = max(smooth_texels, 0.5) * patch / res
    rad = max(1, int(math.ceil(3.0 * sigma_cm / step)))
    offs = np.arange(-rad, rad + 1)
    kernel = np.exp(-0.5 * (offs * step / sigma_cm) ** 2)
    kernel /= kernel.sum()

    acc = [np.zeros((res, res), dtype=np.float64) for _ in range(3)]
    for ci, ior in enumerate(IORS):
        eta = 1.0 / ior
        cosi = -(nx * sun[0] + ny * sun[1] + nzv * sun[2])
        k = 1.0 - eta * eta * (1.0 - cosi * cosi)
        ok = k >= 0.0
        k = np.sqrt(np.maximum(k, 0.0))
        rx = eta * sun[0] + (eta * cosi - k) * nx
        ry = eta * sun[1] + (eta * cosi - k) * ny
        rz = eta * sun[2] + (eta * cosi - k) * nzv

        # March from the surface down to the seabed plane at z = -DEPTH_M.
        safe = np.where(np.abs(rz) > 1e-4, rz, 1e-4)
        s = (-DEPTH_M * 100.0 - z) / safe          # z is in cm, DEPTH_M in metres
        valid = ok & (s > 0.0) & (rz < 0.0)
        fx = X + rx * s
        fy = Y + ry * s
        fx = np.where(valid, fx, np.nan)
        fy = np.where(valid, fy, np.nan)

        # Jacobian of the landing map by central differences on the grid.
        dfx_di = (np.roll(fx, -1, 0) - np.roll(fx, 1, 0)) / (2.0 * step)
        dfy_di = (np.roll(fy, -1, 0) - np.roll(fy, 1, 0)) / (2.0 * step)
        dfx_dj = (np.roll(fx, -1, 1) - np.roll(fx, 1, 1)) / (2.0 * step)
        dfy_dj = (np.roll(fy, -1, 1) - np.roll(fy, 1, 1)) / (2.0 * step)

        det = dfx_di * dfy_dj - dfx_dj * dfy_di
        good = np.isfinite(det) & (det > 1e-6) & np.isfinite(fx) & np.isfinite(fy)
        intensity = np.where(good, 1.0 / np.maximum(det, 1e-6), 0.0)
        # Fold in the cosine of the incidence on the seabed: a grazing landing spreads the
        # same energy over more area.
        intensity *= np.where(good, np.clip(-rz, 0.0, 1.0), 0.0)

        u = np.mod(fx, patch) / patch * res
        v = np.mod(fy, patch) / patch * res
        ui = np.floor(u).astype(np.int64)
        vi = np.floor(v).astype(np.int64)
        fu = u - ui
        fv = v - vi
        ui %= res
        vi %= res

        # Deposit with separable bilinear weights, then the small Gaussian to close the
        # gaps between neighbouring rays.
        for ou, wu in ((0, 1.0 - fu), (1, fu)):
            for ov, wv in ((0, 1.0 - fv), (1, fv)):
                wgt = np.where(good, intensity * wu * wv, 0.0)
                np.add.at(acc[ci], ((vi + ov) % res, (ui + ou) % res), wgt)

        a = acc[ci]
        acc[ci] = _blur_wrap(a, kernel, offs)

    out = np.zeros((res, res, 4), dtype=np.float32)
    for ci in range(3):
        a = acc[ci]
        mean = a.mean()
        out[:, :, ci] = a / mean if mean > 0 else 0.0
    out[:, :, 3] = 1.0
    return out


def _blur_wrap(a, kernel, offs):
    """Separable Gaussian blur with wrap-around, so the tile stays seamless."""
    out = np.zeros_like(a)
    for o, k in zip(offs, kernel):
        out += k * np.roll(a, int(o), axis=0)
    tmp = out
    out = np.zeros_like(a)
    for o, k in zip(offs, kernel):
        out += k * np.roll(tmp, int(o), axis=1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--frames', type=int, default=FRAMES)
    ap.add_argument('--res', type=int, default=RES)
    ap.add_argument('--grid', type=int, default=SURFACE_GRID)
    ap.add_argument('--patch', type=float, default=4.6,
                    help='caustic patch size in metres (small = finer web, more tiling)')
    args = ap.parse_args()

    waves = json.loads(WAVES.read_text(encoding='utf-8'))['waves']
    patch = args.patch
    wf = quantise_periodic(waves, patch * 100.0)   # patch in cm for the rad/cm wavenumbers
    OUT.mkdir(parents=True, exist_ok=True)

    stats = []
    for f in range(args.frames):
        t = LOOP_SECONDS * f / args.frames
        frame = bake_frame(wf, t, args.res, patch * 100.0, args.grid)
        bright = frame[:, :, :3]
        stats.append({'frame': f, 't': round(t, 3),
                      'min': float(bright.min()), 'max': float(bright.max()),
                      'mean': float(bright.mean())})
        if Image is not None:
            # Preview only: the imported texture must stay LINEAR (no gamma, no clamp), so
            # the scale is chosen from the data rather than fixed -- a real caustic peaks
            # one to two orders of magnitude above its mean.
            hi = float(np.percentile(bright, 99.5))
            img = np.clip(bright / max(hi, 1e-6), 0.0, 1.0) ** (1.0 / 2.2)
            stat = np.clip(bright / max(hi, 1e-6), 0.0, 1.0)
            Image.fromarray((stat * 255.0).astype(np.uint8)).save(
                OUT / ('caustics_%02d.png' % f))

    peak = max(s['max'] for s in stats)
    (OUT / 'caustics.json').write_text(json.dumps({
        'frames': args.frames, 'res': args.res, 'patch_m': patch,
        'loop_seconds': LOOP_SECONDS, 'iors': list(IORS),
        'depth_m': DEPTH_M, 'sun_el_deg': SUN_EL_DEG, 'sun_az_deg': SUN_AZ_DEG,
        'surface_grid': args.grid, 'components': len(wf),
        'peak_concentration': round(peak, 2),
        'stats': stats,
    }, indent=2), encoding='utf-8')
    print('CLEARWATER_CAUSTICS ' + json.dumps({
        'frames': args.frames, 'res': args.res, 'patch_m': patch,
        'components': len(wf), 'peak_concentration': round(peak, 2),
        'out': str(OUT), 'png': Image is not None,
    }))


if __name__ == '__main__':
    main()
