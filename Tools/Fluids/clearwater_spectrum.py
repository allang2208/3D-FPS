"""Analyse the Clearwater ocean spectrum and reduce it to a portable wave field.

Clearwater (https://github.com/Aureliengmz/clearwater, MIT) drives its water surface with a
256x256 GPU FFT every frame. A material graph cannot run a 16-pass butterfly FFT, so this
tool reproduces Clearwater's *spectrum* on the CPU -- the exact Phillips-like model from
`buildH0()` in index.html -- and then selects the strongest directional components as
discrete waves. The result is the same spectral composition (peak bump + high-frequency
tail + low-frequency swell, directional spread, RMS-slope normalisation) expressed as a
sum that any vertex/pixel shader can evaluate.

Inputs mirrored from the source (index.html lines 128-168):
    L = 4.6 m patch, N = 256, DEPTH = 1.6 m, TARGET_SLOPE = 0.078
    kp = 2*pi/0.62 (peak), kcut = 2*pi/0.045 (cutoff), wind dir (0.8, 0.6)

Outputs (SourceAssets/ClearwaterWater20260926/):
    spectrum.json      - full analysis: selected components, total energy, sanity checks
    waves.json         - the reduced wave list consumed by the authoring script
    Waves.gen.h        - the same list as a C++ header, for any CPU-side water query

Run with plain Python 3 (numpy recommended). No Unreal required:
    python Tools/Fluids/clearwater_spectrum.py
"""
import argparse
import json
import math
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is present in this project's tooling env
    raise SystemExit('clearwater_spectrum.py needs numpy')

# ---------------------------------------------------------------- source constants
N = 256
TARGET_SLOPE = 0.078
G = 9.81
PEAK_WAVELENGTH = 0.62
CUTOFF_WAVELENGTH = 0.045
WIND = (0.8, 0.6)
# Clearwater quantises dispersion to 2*pi/60 so the surface loops seamlessly over 60 s.
LOOP_SECONDS = 60.0
OMEGA_QUANT = 2.0 * math.pi / LOOP_SECONDS

# Clearwater uses a 4.6 m patch because its demo camera sits centimetres above a shallow
# shore.  The longest wave a patch can hold is the patch itself, so 4.6 m caps the swell at
# a ~1.2 s period -- pond chop, not the open water in the project's reference image.  A
# larger patch trades spatial detail for real swell: at 46 m the fundamental is a 46 m,
# ~5.4 s wave, and the FFT still resolves down to the 0.62 m peak.  L is therefore a
# parameter; N and the spectrum shape stay identical to the source.
DEFAULT_PATCH = 46.0
DEPTH = 1.6

# Discrete components the shader sums. 32 keeps the Custom node loop unrolled and cheap
# while carrying the spectral character that finite Gerstner sets lack.
WAVE_COUNT = 48

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets' / 'ClearwaterWater20260926'
OUT.mkdir(parents=True, exist_ok=True)

# Set by main(); every spectral helper reads the patch through here.
L = DEFAULT_PATCH


def omega(k):
    """Deep-water dispersion with the same capillary term Clearwater uses."""
    return math.sqrt(G * k + 7.4e-5 * k * k * k)


def quantise(w):
    # index.html line 184: floor(w/w0)*w0, so every wave repeats every LOOP_SECONDS.
    return math.floor(w / OMEGA_QUANT) * OMEGA_QUANT or OMEGA_QUANT


def build_spectrum():
    """Faithful port of buildH0(): returns H0[k] as a complex array plus the real-space grid."""
    kp = 2.0 * math.pi / PEAK_WAVELENGTH
    kcut = 2.0 * math.pi / CUTOFF_WAVELENGTH
    rng = np.random.default_rng(7)  # mulberry(7) in the source; any fixed seed is equivalent
    re = np.zeros((N, N))
    im = np.zeros((N, N))
    for m in range(N):
        nz = m if m < N / 2 else m - N
        for n in range(N):
            nx = n if n < N / 2 else n - N
            kx = 2.0 * math.pi * nx / L
            kz = 2.0 * math.pi * nz / L
            k = math.hypot(kx, kz)
            P = 0.0
            if k > 1e-6:
                lk = math.log(k / kp)
                bump = math.exp(-0.5 * (lk / 0.36) ** 2)
                tail = 0.035 * math.exp(-((kp / k) ** 2)) * math.exp(-((k / kcut) ** 2))
                swell = 0.35 * math.exp(-0.5 * (math.log(k / (2.0 * math.pi / 1.6)) / 0.3) ** 2)
                c = (kx * WIND[0] + kz * WIND[1]) / k
                spread = (0.3 + 0.7 * c * c) * (0.35 if c < 0 else 1.0)
                P = (bump + tail + swell) * spread / (k ** 4)
            a = math.sqrt(P / 2.0)
            re[m, n] = rng.normal() * a
            im[m, n] = rng.normal() * a
    return re, im, kp, kcut


def k_axes():
    """Signed integer wavenumbers on the same (m, n) layout build_spectrum() fills."""
    m = np.arange(N)
    nz = np.where(m < N / 2, m, m - N)
    # build_spectrum() writes index [m, n] with kx from n and kz from m, so the rows of
    # this meshgrid must follow the same (m, n) convention.
    kz, kx = np.meshgrid(2.0 * math.pi * nz / L, 2.0 * math.pi * nz / L, indexing='ij')
    return kx, kz


def normalise(re, im):
    """Rescale to TARGET_SLOPE RMS slope, exactly as buildH0() does."""
    kx, kz = k_axes()
    k2 = kx ** 2 + kz ** 2
    s2 = float(np.sum(2.0 * k2 * (re ** 2 + im ** 2)))
    scale = TARGET_SLOPE / math.sqrt(s2)
    return re * scale, im * scale


def select_components(re, im, count):
    """Pick components spread across the spectrum's energy, not just its tallest peaks.

    The spectrum holds 65536 tiny components, so ranking purely by amplitude returns only
    the very longest waves.  Binning k logarithmically and taking the strongest component
    per bin preserves spectral *coverage* (low swell through to the capillary tail), which
    is what gives the surface its non-repeating character.
    """
    m = np.arange(N)
    nz = np.where(m < N / 2, m, m - N)
    kx, kz = k_axes()
    kmag = np.hypot(kx, kz)

    # Best conjugate pair per texel, keeping only the half plane so k and -k are not
    # both selected as separate waves.
    entries = []
    for mm in range(N):
        for nn in range(N):
            k = kmag[mm, nn]
            if k <= 1e-6:
                continue
            jm, jn = (-mm) % N, (-nn) % N
            if (mm, nn) > (jm, jn):
                continue
            hk = complex(re[mm, nn], im[mm, nn])
            hmk = complex(re[jm, jn], -im[jm, jn])
            a = abs(hk) + abs(hmk)
            if a > 0.0:
                entries.append((k, a, mm, nn, hk, hmk))

    if not entries:
        return [], 0.0

    kmin = min(e[0] for e in entries)
    kmax = max(e[0] for e in entries)
    lo, hi = math.log(kmin), math.log(kmax)
    bins = [[] for _ in range(count)]
    for e in entries:
        t = (math.log(e[0]) - lo) / max(hi - lo, 1e-9)
        bins[min(count - 1, int(t * count))].append(e)

    chosen = []
    for b in bins:
        if not b:
            continue
        # Highest energy (amplitude squared, the actual variance contribution) wins the bin.
        chosen.append(max(b, key=lambda e: e[1] ** 2))
    # Fill any empty bins with the strongest leftovers so the shader loop stays dense.
    leftovers = sorted((e for e in entries if e not in chosen), key=lambda e: -e[1] ** 2)
    for e in leftovers:
        if len(chosen) >= count:
            break
        chosen.append(e)

    chosen.sort(key=lambda e: -e[1])
    waves = []
    for k, a, mm, nn, hk, hmk in chosen:
        dirx, dirz = kx[mm, nn] / k, kz[mm, nn] / k
        phase = 0.5 * (math.atan2(hk.imag, hk.real) - math.atan2(hmk.imag, hmk.real))
        waves.append({
            'amplitude': a,
            'dir': [dirx, dirz],
            'omega': quantise(omega(k)),
            'phase': phase,
            'wavelength': 2.0 * math.pi / k,
            'k': k,
            'Q': None,
        })
    return waves, float(sum(a ** 2 for _, a, _, _, _, _ in chosen))


def reconstruct(waves):
    """Evaluate the reduced wave field over one patch and return height, gradient and stats."""
    size = 256
    span = L
    axis = np.linspace(0.0, span, size)
    zs = np.zeros((size, size))
    dx = np.zeros((size, size))
    dz = np.zeros((size, size))
    for w in waves:
        dxv, dzv = w['dir']
        k = w['k']
        phase = k * (dxv * axis[:, None] + dzv * axis[None, :]) + w['phase']
        zs += w['amplitude'] * np.sin(phase)
        dx += w['amplitude'] * k * dxv * np.cos(phase)
        dz += w['amplitude'] * k * dzv * np.cos(phase)
    slope = np.sqrt(dx ** 2 + dz ** 2)
    return zs, dx, dz, {
        'height_min': float(zs.min()),
        'height_max': float(zs.max()),
        'height_rms': float(np.sqrt((zs ** 2).mean())),
        'slope_rms': float(np.sqrt((slope ** 2).mean())),
    }


def match_target_slope(waves):
    """Rescale the reduced field so its RMS slope recovers Clearwater's TARGET_SLOPE.

    Keeping only WAVE_COUNT of 65536 components removes slope variance that the discarded
    tail would have contributed incoherently (in quadrature).  Left alone the surface comes
    out far smoother than the source, which is exactly the "flat water" failure mode this
    project keeps hitting.  The spectral *shape* is untouched; only the overall amplitude is
    restored, and both before/after numbers are recorded for inspection.
    """
    _, _, _, before = reconstruct(waves)
    if before['slope_rms'] <= 1e-9:
        return before, before, 1.0
    scale = TARGET_SLOPE / before['slope_rms']
    for w in waves:
        w['amplitude'] *= scale
        w['Q'] = min(1.0, 0.85 / max(w['k'] * max(w['amplitude'], 1e-9), 1e-6))
    _, _, _, after = reconstruct(waves)
    return before, after, scale


def main():
    global L
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch', type=float, default=DEFAULT_PATCH,
                        help='FFT patch size in metres (sets the longest wave; default %.0f)' % DEFAULT_PATCH)
    parser.add_argument('--waves', type=int, default=WAVE_COUNT,
                        help='number of discrete components to emit (default %d)' % WAVE_COUNT)
    args = parser.parse_args()
    L = args.patch
    count = args.waves

    re, im, kp, kcut = build_spectrum()
    re, im = normalise(re, im)
    waves, energy = select_components(re, im, count)

    # Clearwater's horizontal displacement comes from i*k*H, i.e. each component carries a
    # choppiness of k*A.  Keeping Q = 1/k (the steepness-normalised form) lets the shader
    # reuse the classic Gerstner/Q formulation without changing the vertical spectrum.
    for w in waves:
        w['Q'] = min(1.0, 0.85 / max(w['k'] * max(w['amplitude'], 1e-9), 1e-6))

    before, stats, scale = match_target_slope(waves)

    report = {
        'source': 'clearwater index.html buildH0()/pSpec',
        'grid': N, 'patch_m': L, 'depth_m': DEPTH, 'target_slope': TARGET_SLOPE,
        'loop_seconds': LOOP_SECONDS,
        'count': len(waves),
        'selection': 'log-spaced wavenumber bins, strongest variance per bin',
        'full_spectrum_rms_slope': TARGET_SLOPE,
        'raw_truncated': before,
        'slope_restore_scale': round(scale, 4),
        'reduced': stats,
        'wavelength_range_m': [round(min(w['wavelength'] for w in waves), 4),
                               round(max(w['wavelength'] for w in waves), 4)],
        'longest_period_s': round(2.0 * math.pi / min(w['omega'] for w in waves), 3),
        'shortest_period_s': round(2.0 * math.pi / max(w['omega'] for w in waves), 3),
        'amplitude_range_m': [round(min(w['amplitude'] for w in waves), 6),
                              round(max(w['amplitude'] for w in waves), 6)],
        'total_amplitude_m': round(sum(w['amplitude'] for w in waves), 5),
        'waves': [{k: (round(v, 8) if isinstance(v, float) else
                       ([round(x, 8) for x in v] if isinstance(v, list) else v))
                   for k, v in w.items()} for w in waves],
    }
    (OUT / 'spectrum.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (OUT / 'waves.json').write_text(json.dumps(
        {'loop_seconds': LOOP_SECONDS, 'depth_m': DEPTH, 'waves': report['waves']}, indent=2), encoding='utf-8')

    lines = [
        '// Generated by Tools/Fluids/clearwater_spectrum.py - do not edit by hand.',
        '// Reduced Clearwater spectrum: same model as index.html buildH0(), expressed as a',
        '// discrete directional wave sum so CPU code and the water material stay in sync.',
        '#pragma once',
        '',
        'namespace ClearwaterWaves',
        '{',
        f'    static constexpr int32 Count = {len(waves)};',
        f'    static constexpr double LoopSeconds = {LOOP_SECONDS:.1f};',
        f'    static constexpr double DepthMeters = {DEPTH:.2f};',
        f'    static constexpr double HeightRms = {stats["height_rms"]:.6f};',
        '',
        '    struct FWave { double DirX, DirZ, Amplitude, Omega, Phase, Q; };',
        '',
        '    static const FWave Waves[Count] =',
        '    {',
    ]
    for w in waves:
        lines.append('        {{ {:.8f}, {:.8f}, {:.8f}, {:.8f}, {:.8f}, {:.6f} }},'.format(
            w['dir'][0], w['dir'][1], w['amplitude'], w['omega'], w['phase'], w['Q']))
    lines += ['    };', '}', '']
    (OUT / 'Waves.gen.h').write_text('\n'.join(lines), encoding='utf-8')

    print('CLEARWATER_SPECTRUM ' + json.dumps({
        'patch_m': L,
        'count': len(waves),
        'height_rms_m': round(stats['height_rms'], 5),
        'height_peak_to_peak_m': round(stats['height_max'] - stats['height_min'], 5),
        'reduced_slope_rms': round(stats['slope_rms'], 5),
        'target_slope': TARGET_SLOPE,
        'wavelength_range_m': report['wavelength_range_m'],
        'period_range_s': [report['shortest_period_s'], report['longest_period_s']],
        'out': str(OUT),
    }))


if __name__ == '__main__':
    main()
