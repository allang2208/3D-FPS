"""Diagnostic only: the Close tail that must be rebuilt, and the donor material.

Measures the delivered Close window's post-impact tail (spectrum, decay, level)
and the candidate donor stretches, so the rebuild matches the real tail rather
than inventing a shape.  Writes only into `_wind/`.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
SR = 48000
NPERSEG, NOVERLAP = 2048, 1792
BANDS = [(200, 400), (400, 800), (800, 1600), (1600, 3200), (3200, 6400), (6400, 12000)]

clean, sr = sf.read(HERE / 'Cleaned/715-reloading-wind-reduced.wav', always_2d=True)
raw, _ = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)

# delivered Close window keeps 4.940-5.420; the mechanism ends at the last peak 5.313
CUT = 5.320
TAIL = (CUT, 5.420)
DONORS = {'cleanest': (4.385, 4.915), 'mid': (3.038, 3.190), 'lead': (0.555, 1.055)}


def bp(x, lo, hi=None):
    b = [lo, hi] if hi else lo
    return signal.sosfiltfilt(signal.butter(3, b, fs=SR,
                                            btype='bandpass' if hi else 'lowpass',
                                            output='sos'), x, axis=0)


def dbfs(v):
    return round(float(20 * np.log10(np.sqrt(np.mean(np.asarray(v) ** 2)) + 1e-12)), 2)


def band_curve(x):
    f, P = signal.welch(x, fs=SR, nperseg=NPERSEG, noverlap=NOVERLAP, axis=0)
    P = P.mean(axis=1) if P.ndim > 1 else P
    return np.array([float(np.sum(P[(f >= lo) & (f < hi)])) for lo, hi in BANDS])


def env_profile(x, win_ms=10):
    n = int(win_ms / 1000 * SR)
    idx = range(0, max(1, len(x) - n), n)
    return [round(float(np.sqrt(np.mean(x[i:i + n] ** 2))), 6) for i in idx]


print('== delivered Close tail (%.3f-%.3f s), cleaned source ==' % TAIL)
tail = clean[round(TAIL[0] * SR):round(TAIL[1] * SR)]
print('   length %.1f ms   rms %+.2f dBFS   peak %.5f'
      % (len(tail) / SR * 1000, dbfs(tail), float(np.max(np.abs(tail)))))
print('   band curve dB:', [round(float(10 * np.log10(v + 1e-30)), 1) for v in band_curve(tail)])
print('   decay (10 ms rms):', env_profile(tail))

print()
print('== same tail in the RAW source (before wind reduction) ==')
rtail = raw[round(TAIL[0] * SR):round(TAIL[1] * SR)]
print('   rms %+.2f dBFS   (cleaned is %+.2f dB lower)'
      % (dbfs(rtail), dbfs(rtail) - dbfs(tail)))

print()
print('== donor candidates (cleaned source) ==')
donor_rows = {}
for name, (a, b) in DONORS.items():
    d = clean[round(a * SR):round(b * SR)]
    bc = band_curve(d)
    donor_rows[name] = {'span_s': [a, b], 'length_ms': round(len(d) / SR * 1000, 1),
                        'rms_dbfs': dbfs(d),
                        'band_db': [round(float(10 * np.log10(v + 1e-30)), 1) for v in bc]}
    print('   %-9s %.3f-%.3f s  %6.1f ms  rms %+7.2f dBFS' % (name, a, b, len(d) / SR * 1000, dbfs(d)))
    print('             band dB:', donor_rows[name]['band_db'])

# spectral distance from the tail so the closest donor can be chosen
tail_curve = band_curve(tail)
print()
print('== spectral distance to the tail (RMS dB across bands) ==')
ref = 10 * np.log10(tail_curve + 1e-30)
best = None
for name, r in donor_rows.items():
    cur = np.array(r['band_db'])
    dev = float(np.sqrt(np.mean((cur - ref) ** 2)))
    r['shape_dev_db'] = round(dev, 2)
    print('   %-9s %.2f dB' % (name, dev))
    if best is None or dev < best[1]:
        best = (name, dev)
print('   closest donor: %s (%.2f dB)' % best)

(OUT / 'close_tail.json').write_text(json.dumps(
    {'tail': {'span_s': TAIL, 'rms_dbfs': dbfs(tail), 'band_db': [round(float(10 * np.log10(v + 1e-30)), 1) for v in tail_curve],
              'decay_10ms': env_profile(tail)},
     'donors': donor_rows, 'closest': best[0]}, indent=2), encoding='utf-8')