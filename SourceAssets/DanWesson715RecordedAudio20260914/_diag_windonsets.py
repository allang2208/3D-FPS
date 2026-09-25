"""Diagnostic only: locate every mechanical onset inside the two wind windows.

Trimming must not remove mechanism.  This finds transient onsets on the
broadband high band (where mechanism dominates) and reports the wind-only gaps
between them, so the cut points can be placed in genuinely empty stretches.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
SR = 48000
MECH_BAND = (1500, 8000)
WIND_BAND = (250, 1000)

WINDOWS = [('Eject', 1.700, 2.320), ('Close', 4.880, 5.500)]

raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
mono = raw.mean(axis=1)
sos = signal.butter(3, 200, fs=SR, btype='highpass', output='sos')
base = signal.sosfiltfilt(sos, mono, axis=0)


def dbfs(v):
    return round(float(20 * np.log10(np.sqrt(np.mean(np.asarray(v) ** 2)) + 1e-12)), 2)


def bp(x, lo, hi):
    s = signal.butter(3, [lo, hi], fs=SR, btype='bandpass', output='sos')
    return signal.sosfiltfilt(s, x, axis=0)


def envelope(x, win_ms=5, hop_ms=1):
    n, h = int(win_ms / 1000 * SR), int(hop_ms / 1000 * SR)
    idx = np.arange(0, max(1, len(x) - n), h)
    env = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in idx])
    return idx / SR, 20 * np.log10(env + 1e-12)


report = {}
for name, a, b in WINDOWS:
    seg = base[round(a * SR):round(b * SR)]
    t, m_env = envelope(bp(seg, *MECH_BAND))
    _, w_env = envelope(bp(seg, *WIND_BAND))
    t_abs = t + a

    # transient onsets: local maxima of the smoothed mechanism envelope that
    # stand clear of the local floor
    sm = np.convolve(m_env, np.ones(5) / 5, mode='same')
    floor = np.percentile(sm, 25)
    idx, props = signal.find_peaks(sm, height=floor + 6.0, distance=15)
    peaks = [(round(float(t_abs[i]), 4), round(float(sm[i]), 1)) for i in idx]

    # wind-only stretches: mechanism envelope far below its own peak
    m_peak = float(np.max(m_env))
    quiet = m_env < (m_peak - 18)
    runs, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * .001 >= .030:
                runs.append((round(float(t_abs[start]), 3), round(float(t_abs[i]), 3)))
            start = None
    if start is not None and (len(quiet) - start) * .001 >= .030:
        runs.append((round(float(t_abs[start]), 3), round(float(t_abs[-1]), 3)))

    report[name] = {
        'window_s': [a, b],
        'mech_peak_db': round(m_peak, 1),
        'transients': peaks,
        'wind_only_runs': runs,
        'wind_env_median_db': round(float(np.median(w_env)), 1),
    }
    print('== %s  (window %.3f-%.3f s) ==' % (name, a, b))
    print('   mechanism envelope peak %+.1f dB; wind median %+.1f dB'
          % (m_peak, float(np.median(w_env))))
    print('   mechanical onsets (local maxima >6 dB over the window floor):')
    for ts, lv in peaks:
        print('      %.4f s   (%+.1f dB)' % (ts, lv))
    print('   wind-only stretches (mechanism >18 dB down, >=30 ms):')
    for s, e in runs:
        print('      %.3f - %.3f s   (%.0f ms)' % (s, e, (e - s) * 1000))
    print()

(OUT / 'wind_onsets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')