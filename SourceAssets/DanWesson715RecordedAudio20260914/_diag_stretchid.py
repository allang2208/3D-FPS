"""Diagnostic only: identity of the wind-led stretches found in both clips.

The per-slice profile shows wind-band energy leading the mechanism band for most
of both windows.  Before acting, this checks whether the low-band energy in those
stretches is wind or the mechanism's own low-frequency resonance, using the same
spectral-shape test that separated wind from mechanism earlier.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
SR = 48000
BANDS = [(200, 400), (400, 800), (800, 1600), (1600, 3200), (3200, 6400), (6400, 12000)]

raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
clean, _ = sf.read(HERE / 'Cleaned/715-reloading-wind-reduced.wav', always_2d=True)

REF = {
    'pure wind (0.555-1.055)': (0.555, 1.055),
    'pure wind (2.230-2.757)': (2.230, 2.757),
    'quietest (4.385-4.915)': (4.385, 4.915),
    'Close impact (5.000-5.020)': (5.000, 5.020),
    'Close peak (5.280-5.320)': (5.280, 5.320),
}
TESTS = {
    'Close 5.020-5.200 (wind-led)': (5.020, 5.200),
    'Close 5.060-5.120 (worst)': (5.060, 5.120),
    'Close 5.160-5.200 (wind-led)': (5.160, 5.200),
    'Close 5.240-5.280 (wind-led)': (5.240, 5.280),
    'Close 5.340-5.400 (tail)': (5.340, 5.400),
    'Eject 1.800-1.945 (lead)': (1.800, 1.945),
    'Eject 1.920-1.940 (gust)': (1.920, 1.940),
    'Eject 2.120-2.220 (decay)': (2.120, 2.220),
    'Eject 2.040-2.080 (impact)': (2.040, 2.080),
}


def shape_of(x):
    n = min(2048, len(x))
    n -= n % 2
    f, P = signal.welch(x, fs=SR, nperseg=n, noverlap=n // 2, axis=0)
    P = P.mean(axis=1) if P.ndim > 1 else P
    bc = np.array([float(np.sum(P[(f >= lo) & (f < hi)])) for lo, hi in BANDS])
    tot = float(bc.sum()) + 1e-30
    return np.array([10 * np.log10(v + 1e-30) - 10 * np.log10(tot) for v in bc]), \
        float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12))


def dist(a, b):
    return round(float(np.sqrt(np.mean((a - b) ** 2))), 2)


refs = {}
for label, (a, b) in REF.items():
    s, lv = shape_of(raw[round(a * SR):round(b * SR)])
    refs[label] = s
    print('ref %-30s rms %+7.2f dBFS  shape %s' % (label, lv, [round(float(v), 1) for v in s]))

print()
print('%-32s%9s   %s' % ('stretch', 'rms dB', 'shape distance to each reference (dB)'))
rows = []
for label, (a, b) in TESTS.items():
    s, lv = shape_of(raw[round(a * SR):round(b * SR)])
    d = {k: dist(s, v) for k, v in refs.items()}
    rows.append({'stretch': label, 'span_s': [a, b], 'rms_dbfs': round(lv, 2),
                 'distances': d,
                 'closest': min(d, key=d.get)})
    print('%-32s%9.2f   %s' % (label, lv,
                               '  '.join('%s=%.1f' % (k.split(' ')[0], v) for k, v in d.items())))
    print('%-32s%9s   closest: %s' % ('', '', min(d, key=d.get)))

(OUT / 'stretch_identity.json').write_text(json.dumps({'refs': REF, 'rows': rows}, indent=2),
                                           encoding='utf-8')